import os
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Redireciona stdout e stderr se estiver a correr em pythonw.exe (sem consola)
if sys.stdout is None:
    try:
        sys.stdout = open(BASE_DIR / "out.log", "a", encoding="utf-8", buffering=1)
    except Exception:
        sys.stdout = open(os.devnull, "w")

if sys.stderr is None:
    try:
        sys.stderr = open(BASE_DIR / "err.log", "a", encoding="utf-8", buffering=1)
    except Exception:
        sys.stderr = open(os.devnull, "w")

# Configura encoding UTF-8 na consola do Windows
if sys.platform.startswith("win"):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# Aplica correcao de certificados SSL para Windows
from app.core.ssl_patch import apply_ssl_fix
apply_ssl_fix()

import uvicorn

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("          INICIANDO NETCONTACTOS (FastAPI + Sherlock)       ")
        print("=" * 60)
        print(" Dashboard Web: http://localhost:8000")
        print(" Swagger Docs:  http://localhost:8000/docs")
        print("=" * 60)
        print(" Pressione Ctrl+C para encerrar o servidor.\n")
    except Exception:
        pass
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
