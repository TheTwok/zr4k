import os
import sys
import uvicorn

class Tee:
    def __init__(self, filename, stream):
        self.file = open(filename, "a", encoding="utf-8", buffering=1)
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.file.write(data)

    def flush(self):
        self.stream.flush()
        self.file.flush()

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    print("=== ZR4K Unified Single-Process Service Runner ===")
    
    # Redirect stdout and stderr to a persistent log file on Bothost
    if os.path.exists("/app/data"):
        log_file = "/app/data/console.log"
        print(f"📝 Redirecting console output to persistent log: {log_file}")
        sys.stdout = Tee(log_file, sys.stdout)
        sys.stderr = Tee(log_file, sys.stderr)

        # Copy sessions and DB from shared storage if they exist there
        shared_dir = os.getenv("SHARED_DIR", "/app/shared")
        data_dir = "/app/data"
        if os.path.exists(shared_dir):
            print(f"📦 Shared storage found at {shared_dir}. Checking files...")
            import shutil
            
            # 1. zr4k.db
            shared_db = os.path.join(shared_dir, "zr4k.db")
            target_db = os.path.join(data_dir, "zr4k.db")
            if os.path.exists(shared_db):
                if not os.path.exists(target_db):
                    print(f"💾 Copying database from shared storage: {shared_db} -> {target_db}")
                    try:
                        shutil.copy2(shared_db, target_db)
                        os.chmod(target_db, 0o777)
                    except Exception as e:
                        print(f"❌ Error copying database: {e}")
                else:
                    print(f"💾 Database already exists at {target_db}. Skipping copy.")
            else:
                print(f"💾 No zr4k.db found in shared storage.")
                    
            # 2. sessions
            sessions_dir = os.path.join(data_dir, "sessions")
            os.makedirs(sessions_dir, exist_ok=True)
            try:
                os.chmod(sessions_dir, 0o777)
            except Exception:
                pass
                
            for f in os.listdir(shared_dir):
                if f.endswith(".session") or f.endswith(".session-journal"):
                    shared_session = os.path.join(shared_dir, f)
                    target_session = os.path.join(sessions_dir, f)
                    if not os.path.exists(target_session):
                        print(f"🔑 Copying session from shared storage: {shared_session} -> {target_session}")
                        try:
                            shutil.copy2(shared_session, target_session)
                            os.chmod(target_session, 0o777)
                        except Exception as e:
                            print(f"❌ Error copying session file {f}: {e}")
                    else:
                        print(f"🔑 Session file {f} already exists at {target_session}. Skipping copy.")

    port = int(os.getenv("PORT", "8000"))
    print(f"🚀 Starting Uvicorn server on http://0.0.0.0:{port}...")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
