import os
import sys
import re
import asyncio
import certifi
from typing import AsyncGenerator, Dict, Any

MAIGRET_FOUND_REGEX = re.compile(r"\[\+\]\s+([^:]+):\s+(https?://[^\s]+)")

async def stream_maigret(username: str, top_sites: int = 150) -> AsyncGenerator[Dict[str, Any], None]:
    """Executa o Maigret em subprocesso assíncrono com ranking Alexa e faz stream em tempo real."""
    python_exe = sys.executable
    cmd = [
        python_exe,
        "-m",
        "maigret",
        username,
        "--top-sites", str(top_sites),
        "--no-progressbar",
        "--no-color",
        "--timeout", "10",
        "--no-recursion"
    ]

    env = os.environ.copy()
    ca = certifi.where()
    env["SSL_CERT_FILE"] = ca
    env["REQUESTS_CA_BUNDLE"] = ca
    env["PYTHONUNBUFFERED"] = "1"

    yield {"type": "start", "engine": "Maigret", "username": username, "top_sites": top_sites}

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

            match = MAIGRET_FOUND_REGEX.search(line)
            if match:
                site = match.group(1).strip()
                url = match.group(2).strip()
                yield {
                    "type": "found",
                    "engine": "Maigret",
                    "site": site,
                    "url": url,
                    "status": "active"
                }
            elif "[*]" in line or "Searching" in line:
                yield {"type": "progress", "message": line}

        await process.wait()
        yield {"type": "completed", "engine": "Maigret"}

    except Exception as e:
        yield {"type": "error", "message": str(e)}
