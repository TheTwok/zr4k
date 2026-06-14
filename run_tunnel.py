import subprocess
import re
import os
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def update_env(new_url):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, "backend", ".env")
    if not os.path.exists(env_path):
        print(f"❌ Файл {env_path} не найден.")
        return False
        
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Заменяем строчку APP_URL=...
    pattern = r"APP_URL=[^\n]*"
    if re.search(pattern, content):
        new_content = re.sub(pattern, f"APP_URL={new_url}", content)
    else:
        new_content = content + f"\nAPP_URL={new_url}"
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print(f"📝 Файл .env успешно обновлен! APP_URL={new_url}")
    return True

def main():
    print("=== ZR4K: Автоматический HTTPS Туннель ===")
    print("🚀 Запуск туннеля через npx localtunnel на порт 8000...")
    
    # Запускаем localtunnel через cmd
    # localtunnel иногда требует подтверждения при первом запуске, npx -y согласится автоматически
    cmd = "cmd.exe /c \"npx -y localtunnel --port 8000\""
    
    try:
        proc = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            shell=True
        )
    except Exception as e:
        print(f"❌ Не удалось запустить туннель: {e}")
        return

    url_detected = False
    
    # Читаем вывод утилиты построчно
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            
            clean_line = line.strip()
            print(f"[Tunnel Log] {clean_line}")
            
            # Ищем ссылку в выводе localtunnel
            # Формат: "your url is: https://xxxx.loca.lt"
            match = re.search(r"your url is:\s*(https://[a-zA-Z0-9.-]+)", clean_line, re.IGNORECASE)
            if match:
                url = match.group(1)
                print(f"\n🔑 Найдена HTTPS ссылка: {url}")
                
                # Обновляем .env
                if update_env(url):
                    url_detected = True
                    print("\n✨ Туннель успешно настроен!")
                    print("👉 Теперь ПЕРЕЗАПУСТИТЕ run.py, чтобы применить настройки.")
                    print("🔔 После этого откройте бота в Telegram и напишите /start.")
                    print("\n⚠️ ВНИМАНИЕ: Не закрывайте это окно терминала, иначе туннель отключится!")
            
            # Небольшая пауза, чтобы не нагружать процессор
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Отключение туннеля...")
    finally:
        proc.terminate()
        proc.wait()
        print("🔌 Туннель закрыт.")

if __name__ == "__main__":
    main()
