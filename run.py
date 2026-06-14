import subprocess
import sys
import os
import time
import re
import threading
import urllib.request
import socket

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def get_env_app_url():
    val = os.getenv("APP_URL")
    if val:
        return val
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, "backend", ".env")
    if not os.path.exists(env_path):
        return None
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("APP_URL="):
                return line.strip().split("=", 1)[1].strip()
    return None

def get_env_ngrok_token():
    val = os.getenv("NGROK_AUTHTOKEN")
    if val:
        return val
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, "backend", ".env")
    if not os.path.exists(env_path):
        return None
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("NGROK_AUTHTOKEN="):
                return line.strip().split("=", 1)[1].strip()
    return None

def update_env(new_url):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, "backend", ".env")
    if not os.path.exists(env_path):
        return False
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r"APP_URL=[^\n]*"
    if re.search(pattern, content):
        new_content = re.sub(pattern, f"APP_URL={new_url}", content)
    else:
        new_content = content + f"\nAPP_URL={new_url}"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True

def download_cloudflared(dest_path):
    print("📥 Downloading cloudflared binary... Please wait, this might take a few seconds.")
    if sys.platform == "win32":
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    else:
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        urllib.request.urlretrieve(url, dest_path)
        if sys.platform != "win32":
            os.chmod(dest_path, 0o755)
        print("✅ cloudflared binary downloaded successfully.")
        return True
    except Exception as e:
        print(f"❌ Failed to download cloudflared: {e}")
        return False

def consume_stdout(proc):
    while True:
        line = proc.stdout.readline()
        if not line:
            break

def is_port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False

import urllib.error

def check_tunnel_healthy(url):
    """
    Pings the public tunnel URL.
    Returns True if healthy (200 OK, 304, or any server-level response like 401/404/405).
    Returns False if Cloudflare itself returns an error (1033, 502, 503, 504) or connection fails.
    """
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ZR4K-Monitor/1.0'}
        )
        with urllib.request.urlopen(req, timeout=5.0) as response:
            if response.getcode() in [200, 304]:
                return True
    except urllib.error.HTTPError as e:
        # If the backend responded (e.g. 404, 401, 405), the tunnel itself is up and running.
        # Cloudflare's own errors are usually 1033, 502, 503, 504.
        if e.code in [1033, 502, 503, 504]:
            return False
        return True
    except (urllib.error.URLError, OSError, ConnectionError, TimeoutError):
        return False
    except Exception:
        return False


def main():
    print("=== ZR4K: All-in-One Service Runner ===")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    if sys.platform == "win32":
        venv_python = os.path.join(base_dir, "backend", ".venv", "Scripts", "python.exe")
        cf_bin = os.path.join(base_dir, "backend", "cloudflared.exe")
    else:
        venv_python = os.path.join(base_dir, "backend", ".venv", "bin", "python")
        cf_bin = os.path.join(base_dir, "backend", "cloudflared")
    
    if not os.path.exists(venv_python):
        print(f"ℹ️ Virtual environment not found. Using system python: {sys.executable}")
        venv_python = sys.executable
        
    tunnel_proc = None
    bot_proc = None
    parser_proc = None
    arq_proc = None

    
    # 1. Start FastAPI backend (uvicorn) first
    print("🚀 Starting FastAPI backend on http://0.0.0.0:8000...")
    backend_proc = subprocess.Popen([
        venv_python, "-m", "uvicorn", "backend.app.main:app", 
        "--host", "0.0.0.0", "--port", "8000"
    ], cwd=base_dir)
    
    # Wait for backend to bind to the port
    print("⏳ Waiting for FastAPI backend to bind to port 8000...")
    backend_ready = False
    for _ in range(30): # 15 seconds timeout
        if is_port_open("127.0.0.1", 8000):
            backend_ready = True
            break
        time.sleep(0.5)
        
    if not backend_ready:
        print("❌ Error: FastAPI backend failed to start on port 8000.")
        backend_proc.terminate()
        sys.exit(1)
        
    print("✅ FastAPI backend is ready and listening.")

    # 2. Check if tunnel is needed
    app_url = get_env_app_url() or "http://localhost:8000"
    is_https = app_url.startswith("https://")
    is_local = "localhost" in app_url or "127.0.0.1" in app_url
    is_tunnel = "loca.lt" in app_url or "ngrok" in app_url or "pinggy" in app_url or "trycloudflare.com" in app_url
    
    tunnel_needed = not is_https or is_local or is_tunnel
    
    # Check if running inside a container (Docker/K8s/etc.)
    # On Apply.Build and most clouds, the OS is Linux (sys.platform != "win32")
    if sys.platform != "win32" or os.path.exists('/.dockerenv') or os.getenv('K_SERVICE') or os.getenv('DOCKER_ENV') or os.getenv('PORT'):
        print("🐳 Container/Cloud environment detected. Disabling automatic local tunnel.")
        tunnel_needed = False
        
    if tunnel_needed:
        print("🌐 Starting automatic Cloudflare Tunnel (TryCloudflare)...")
        
        # Download cloudflared if not exists
        if not os.path.exists(cf_bin):
            success = download_cloudflared(cf_bin)
            if not success:
                print("❌ Cannot proceed without cloudflared. Exiting.")
                backend_proc.terminate()
                sys.exit(1)
                
        cmd = [cf_bin, "tunnel", "--url", "http://127.0.0.1:8000"]
        
        try:
            tunnel_proc = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True
            )
            
            print("⏳ Waiting for public HTTPS URL from TryCloudflare...")
            url = None
            start_time = time.time()
            while time.time() - start_time < 30: # 30 seconds timeout
                line = tunnel_proc.stdout.readline()
                if not line:
                    break
                clean_line = line.strip()
                match = re.search(r"(https://[a-zA-Z0-9.-]+\.trycloudflare\.com)", clean_line, re.IGNORECASE)
                if match:
                    url = match.group(1)
                    break
                time.sleep(0.05)
                
            if url:
                print(f"🔑 Public HTTPS URL obtained: {url}")
                os.environ["APP_URL"] = url
                update_env(url)
                
                t = threading.Thread(target=consume_stdout, args=(tunnel_proc,), daemon=True)
                t.start()
                
                print("⏳ Waiting for public tunnel URL to propagate and become active on Cloudflare edge...")
                tunnel_ready = False
                for i in range(40): # Up to ~60 seconds timeout
                    if check_tunnel_healthy(url):
                        tunnel_ready = True
                        break
                    if i > 0 and i % 5 == 0:
                        print(f"   ...still waiting ({i}s)")
                    time.sleep(1.5)
                
                if tunnel_ready:
                    print("✅ Public tunnel is active and reachable on the internet.")
                else:
                    print("⚠️ Public tunnel propagation is taking longer than expected. Proceeding...")
            else:
                print("⚠️ Failed to obtain tunnel URL in 30 seconds. Proceeding without tunnel...")
        except Exception as e:
            print(f"❌ Failed to start Cloudflare Tunnel: {e}")
    else:
        print(f"🚀 Using configured APP_URL: {app_url} (No tunnel started)")

    try:
        # Give a small buffer for the tunnel network configuration
        time.sleep(0.5)

        # 3. Start Client Bot (aiogram)
        print("🤖 Starting Telegram Client Bot...")
        bot_proc = subprocess.Popen([
            venv_python, "backend/bot.py"
        ], cwd=base_dir)
        
        # 4. Start Parser Bot (Telethon)
        print("🕵️ Starting Userbot Parser...")
        parser_proc = subprocess.Popen([
            venv_python, "backend/parser.py"
        ], cwd=base_dir)
        
        # 5. Start Arq Worker (tasks)
        print("⏰ Starting Arq Worker...")
        arq_proc = subprocess.Popen([
            venv_python, "-m", "arq", "backend.app.tasks.WorkerSettings"
        ], cwd=base_dir)

        
        print("\n✨ All services successfully started! Press Ctrl+C to terminate.")
        tunnel_verified = True # Already verified synchronously at startup
        if tunnel_needed:
            print("🔄 Авто-восстановление: Запущен фоновый мониторинг туннеля. При обрыве связи (Error 1033) адрес обновится автоматически!")
        
        consecutive_failures = 0
        last_ping_time = time.time()
        
        # Monitor processes & Self-heal tunnel drops
        while True:
            # Check if critical services died
            if backend_proc.poll() is not None:
                print(f"\n❌ Backend process died (exit code {backend_proc.returncode}). Shutting down...")
                break
            if parser_proc.poll() is not None:
                print(f"\n❌ Parser process died (exit code {parser_proc.returncode}). Shutting down...")
                break
            if bot_proc and bot_proc.poll() is not None:
                print(f"\n❌ Bot process died (exit code {bot_proc.returncode}). Shutting down...")
                break
            if arq_proc and arq_proc.poll() is not None:
                print(f"\n❌ Arq worker process died (exit code {arq_proc.returncode}). Shutting down...")
                break
            if tunnel_proc and tunnel_proc.poll() is not None:
                print(f"\n⚠️ Tunnel process died (exit code {tunnel_proc.returncode}). Attempting automatic recovery...")
                consecutive_failures = 3 # Trigger recovery immediately
                
            # Regular tunnel ping check every 20 seconds
            if tunnel_needed and tunnel_verified and time.time() - last_ping_time > 20:
                last_ping_time = time.time()
                current_url = get_env_app_url()
                if current_url:
                    is_healthy = check_tunnel_healthy(current_url)
                    if not is_healthy:
                        consecutive_failures += 1
                        print(f"⚠️ [Self-Healing] Public tunnel healthcheck failed ({consecutive_failures}/3)...")
                    else:
                        if consecutive_failures > 0:
                            print("✅ [Self-Healing] Tunnel connection healthy.")
                        consecutive_failures = 0
                        
            # If tunnel fails 3 times in a row, rebuild it
            if consecutive_failures >= 3:
                print("\n🚨 [Self-Healing] Tunnel is unresponsive. Rebuilding Cloudflare Tunnel...")
                consecutive_failures = 0
                
                # A. Stop old cloudflared
                print("Stopping old tunnel process...")
                try:
                    if tunnel_proc:
                        tunnel_proc.terminate()
                        tunnel_proc.wait(timeout=5)
                except Exception:
                    pass
                
                # B. Start new cloudflared
                print("Starting new Cloudflare Tunnel...")
                cmd = [cf_bin, "tunnel", "--url", "http://127.0.0.1:8000"]
                try:
                    tunnel_proc = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, 
                        text=True
                    )
                    
                    # C. Wait for new URL
                    print("⏳ Waiting for new public HTTPS URL...")
                    new_url = None
                    tunnel_start_time = time.time()
                    while time.time() - tunnel_start_time < 35:
                        line = tunnel_proc.stdout.readline()
                        if not line:
                            break
                        clean_line = line.strip()
                        match = re.search(r"(https://[a-zA-Z0-9.-]+\.trycloudflare\.com)", clean_line, re.IGNORECASE)
                        if match:
                            new_url = match.group(1)
                            break
                        time.sleep(0.05)
                        
                    if new_url:
                        print(f"🔑 New public HTTPS URL obtained: {new_url}")
                        os.environ["APP_URL"] = new_url
                        update_env(new_url)
                        
                        # Restart background reader thread
                        t = threading.Thread(target=consume_stdout, args=(tunnel_proc,), daemon=True)
                        t.start()
                        
                        # D. Hot-restart Bot to register new WebApp button URL in Telegram
                        print("🔄 Hot-restarting Client Bot to register new URL in Telegram...")
                        try:
                            if bot_proc:
                                bot_proc.terminate()
                                bot_proc.wait(timeout=5)
                        except Exception:
                            pass
                        
                        bot_proc = subprocess.Popen([
                            venv_python, "backend/bot.py"
                        ], cwd=base_dir)
                        print("✅ Client Bot hot-restarted successfully.")
                    else:
                        print("❌ Failed to obtain new tunnel URL. Will retry in next check cycle.")
                except Exception as e:
                    print(f"❌ Failed to recover tunnel: {e}")
                    
            time.sleep(1)
            
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 Shutting down all services...")
        active_procs = [backend_proc, tunnel_proc, bot_proc, parser_proc, arq_proc]
        for p in active_procs:
            if p and p.poll() is None:
                try:
                    print(f"Stopping process {p.pid}...")
                    p.terminate()
                    p.wait(timeout=5)
                except Exception:
                    pass
        print("✅ All processes terminated.")

if __name__ == "__main__":
    main()
