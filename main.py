import os
import subprocess
import json
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import base64

app = FastAPI(title="GalleryDL Microservice", version="2.0")

BASE_TEMP = Path("/tmp/gallerydl")
BASE_TEMP.mkdir(exist_ok=True)

class DownloadRequest(BaseModel):
    url: str

def run_gallery_dl(url: str, output_dir: Path):
    cmd = [
        "gallery-dl",
        "--ignore-config",
        "-d", str(output_dir),
        url
    ]

    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=90
    )

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "Erro desconhecido do gallery-dl")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/download")
def download(req: DownloadRequest):
    job_id = f"job-{uuid.uuid4()}"
    temp_dir = BASE_TEMP / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        run_gallery_dl(req.url, temp_dir)

        files = list(temp_dir.glob("**/*"))

        if not files:
            raise HTTPException(500, "Nenhum arquivo encontrado.")

        responses = []

        for file in files:
            if not file.is_file():
                continue

            ext = file.suffix.lower()

            mime = {
                ".mp4": "video/mp4",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }.get(ext, "application/octet-stream")

            # Converte arquivo para base64 para o n8n interpretar como binary
            with open(file, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            responses.append({
                "binary": {
                    "data": {
                        "data": b64,
                        "fileName": file.name,
                        "mimeType": mime
                    }
                }
            })

        return responses

    except Exception as e:
        raise HTTPException(500, str(e))

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
