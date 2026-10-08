import os
import sys
import re
import asyncio
import certifi
from typing import AsyncGenerator, Dict, Any

FOUND_REGEX = re.compile(r"^\[\+\]\s*([^:]+):\s*(https?://[^\s]+)")

async def stream_sherlock(username: str, timeout: int = 180) -> AsyncGenerator[Dict[str, Any], None]:
    """Executa o Sherlock em subprocesso assíncrono com SSL configurado e faz stream dos perfis encontrados."""
    python_exe = sys.executable
    cmd = [
        python_exe,
        "-m",
        "sherlock_project",
        username,
        "--print-found",
        "--no-color",
        "--timeout", "10"
    ]

    # Garante certificados SSL no subprocesso
    env = os.environ.copy()
    ca = certifi.where()
    env["SSL_CERT_FILE"] = ca
    env["REQUESTS_CA_BUNDLE"] = ca
    env["PYTHONUNBUFFERED"] = "1"

    yield {"type": "start", "engine": "Sherlock", "username": username}

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        while True:
            line_bytes = await process.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode(errors="ignore").strip()
            if not line:
                continue

            match = FOUND_REGEX.match(line)
            if match:
                site = match.group(1).strip()
                url = match.group(2).strip()
                yield {
                    "type": "found",
                    "engine": "Sherlock",
                    "site": site,
                    "url": url,
                    "status": "active"
                }
            elif line.startswith("[*]"):
                yield {"type": "progress", "message": line}

        await process.wait()
        yield {"type": "completed", "engine": "Sherlock"}

    except Exception as e:
        yield {"type": "error", "message": str(e)}
