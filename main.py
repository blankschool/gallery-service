import os
import subprocess
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

DOWNLOAD_DIR = "/app/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("CMD:", " ".join(cmd))
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    return result


@app.post("/download")
async def download(url: str):
    file_id = str(uuid.uuid4())[:8]
    temp_dir = f"{DOWNLOAD_DIR}/{file_id}"
    os.makedirs(temp_dir, exist_ok=True)

    # Cookies corretos
    if "instagram.com" in url:
        cookie_file = "/app/cookies/instagram.txt"
    elif "tiktok.com" in url:
        cookie_file = "/app/cookies/tiktok.txt"
    else:
        raise HTTPException(status_code=400, detail="URL não suportada")

    # Comando gallery-dl sem --no-cache
    cmd = [
        "gallery-dl",
        "--cookies", cookie_file,
        "-o", f"base-directory={temp_dir}",
        url
    ]

    result = run_cmd(cmd)

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Erro executando gallery-dl: {result.stderr}"
        )

    files = os.listdir(temp_dir)
    if not files:
        raise HTTPException(status_code=500, detail="Nenhum arquivo baixado")

    file_path = os.path.join(temp_dir, files[0])

    return FileResponse(
        file_path,
        filename=files[0],
        media_type="application/octet-stream"
    )
