"""Root-level entry point to start the Next EUV Local Website Server."""

import sys
from pathlib import Path

# Add nexteuv directory to sys.path and run
nexteuv_dir = Path(__file__).resolve().parent / "nexteuv"
sys.path.insert(0, str(nexteuv_dir))

import server

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    server.run(port)
