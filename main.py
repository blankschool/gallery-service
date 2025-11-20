import os
import subprocess
import json
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="GalleryDL Microservice", version="1.0")

BASE_DIR = Path(__file__).resolve().parent
BASE_TEMP = Path("/tmp/gallerydl")
BASE_TEMP.mkdir(exist_ok=True)

INSTAGRAM_COOKIES = BASE_DIR / "instagram.txt"


class DownloadRequest(BaseModel):
    url: str


def build_gallery_cmd(url: str, output_dir: Path | None = None, dump_json=False):
    cmd = ["gallery-dl", "--ignore-config"]

    if dump_json:
        cmd.append("--dump-json")

    if output_dir:
        cmd += ["-d", str(output_dir)]

    if "instagram.com" in url:
        cmd += ["--cookies", str(INSTAGRAM_COOKIES)]

    cmd.append(url)
    return cmd


@app.post("/fetch")
def fetch(req: DownloadRequest):
    """
    Retorna TODOS os metadados exatamente como o gallery-dl entrega,
    ignorando warnings e linhas inválidas.
    """
    cmd = build_gallery_cmd(req.url, dump_json=True)

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or "Erro desconhecido")

        json_objects = []

        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                json_objects.append(obj)
            except json.JSONDecodeError:
                # ignora warnings do gallery-dl
                continue

        if not json_objects:
            raise RuntimeError("Nenhum JSON válido retornado pelo gallery-dl")

        # se tiver só um objeto → retorna direto
        if len(json_objects) == 1:
            return json_objects[0]

        # senão → carrossel completo
        return json_objects

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/download")
def download(req: DownloadRequest):
    """
    DOWNLOAD DE APENAS 1 ITEM.
    O n8n usará /fetch → obterá media_url → HTTP Request → download binário.
    """
    temp_dir = BASE_TEMP / f"job-{uuid.uuid4()}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        cmd = build_gallery_cmd(req.url, output_dir=temp_dir)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr)

        # pega apenas 1 arquivo (uso interno)
        files = [f for f in temp_dir.glob("**/*") if f.is_file()]
        if not files:
            raise HTTPException(status_code=500, detail="Nenhum arquivo baixado.")

        file = files[0]
        data = file.read_bytes()

        ext = file.suffix.lower()
        mime = {
            ".mp4": "video/mp4",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")

        return Response(
            content=data,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{file.name}"'}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
