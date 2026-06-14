import os
import sys
import uvicorn

def get_port() -> int:
    for key in ("PORT", "APP_PORT", "WEB_PORT", "BOTHOST_PORT"):
        value = os.getenv(key)
        if not value:
            continue
        try:
            return int(value.strip("'\" "))
        except ValueError:
            print(f"Ignoring invalid {key} value: {value!r}")
    return 8000

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

    def isatty(self):
        return hasattr(self.stream, 'isatty') and self.stream.isatty()

    def fileno(self):
        return self.stream.fileno()

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
            
            # Helper to get files by extension sorted by modification time (newest first)
            def get_newest_files(directory, extension):
                try:
                    files = [f for f in os.listdir(directory) if f.endswith(extension)]
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)
                    return files
                except Exception as e:
                    print(f"⚠️ Error listing files for {extension}: {e}")
                    return []

            # 1. Copy the newest .db file to zr4k.db
            db_files = get_newest_files(shared_dir, ".db")
            target_db = os.path.join(data_dir, "zr4k.db")
            if db_files:
                shared_db = os.path.join(shared_dir, db_files[0])
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
                print(f"💾 No .db files found in shared storage.")
                    
            # 2. Copy the newest .session file to userbot_79892958989.session
            sessions_dir = os.path.join(data_dir, "sessions")
            os.makedirs(sessions_dir, exist_ok=True)
            try:
                os.chmod(sessions_dir, 0o777)
            except Exception:
                pass
                
            session_files = get_newest_files(shared_dir, ".session")
            if session_files:
                shared_session = os.path.join(shared_dir, session_files[0])
                # Destination must match the registered userbot session name in db: userbot_79892958989.session
                target_session = os.path.join(sessions_dir, "userbot_79892958989.session")
                if not os.path.exists(target_session):
                    print(f"🔑 Copying session from shared storage: {shared_session} -> {target_session}")
                    try:
                        shutil.copy2(shared_session, target_session)
                        os.chmod(target_session, 0o777)
                    except Exception as e:
                        print(f"❌ Error copying session file: {e}")
                else:
                    print(f"🔑 Session file already exists at {target_session}. Skipping copy.")
            else:
                print(f"🔑 No .session files found in shared storage.")

    port = get_port()
    print(f"🚀 Starting Uvicorn server on http://0.0.0.0:{port}...")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
