import os
import sys
import uvicorn
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Aplica correção de certificados SSL para Windows
from app.core.ssl_patch import apply_ssl_fix
apply_ssl_fix()

if __name__ == "__main__":
    print("=" * 60)
    print("       🚀 INICIANDO OSINT HUB (FastAPI + Sherlock)      ")
    print("=" * 60)
    print(" 🌐 Dashboard Web: http://localhost:8000")
    print(" 📚 Swagger Docs:  http://localhost:8000/docs")
    print("=" * 60)
    print(" Pressione Ctrl+C para encerrar o servidor.\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
