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

    port = int(os.getenv("PORT", "8000"))
    print(f"🚀 Starting Uvicorn server on http://0.0.0.0:{port}...")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port)
