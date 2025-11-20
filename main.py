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

# caminho do cookie do Instagram dentro da imagem
INSTAGRAM_COOKIES = BASE_DIR / "instagram.txt"


class DownloadRequest(BaseModel):
    url: str


def build_gallery_cmd(url: str, output_dir: Path) -> list[str]:
    """
    Monta o comando do gallery-dl, adicionando cookies se for Instagram.
    """
    cmd = [
        "gallery-dl",
        "--ignore-config",
        "-d", str(output_dir),
    ]

    # Se for Instagram, usar cookies
    if "instagram.com" in url:
        cmd += ["--cookies", str(INSTAGRAM_COOKIES)]

    cmd.append(url)
    return cmd


def run_gallery_dl(url: str, output_dir: Path):
    """
    Executa o gallery-dl para baixar arquivos no diretório fornecido.
    """
    cmd = build_gallery_cmd(url, output_dir)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print("CMD:", " ".join(cmd))
        print("STDOUT:", proc.stdout)
        print("STDERR:", proc.stderr)

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or "Erro desconhecido do gallery-dl")

    except Exception as e:
        raise RuntimeError(f"Erro executando gallery-dl: {e}")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "gallery-dl",
        "instagram_cookies_exists": INSTAGRAM_COOKIES.exists(),
    }


@app.post("/fetch")
def fetch(req: DownloadRequest):
    """
    Retorna metadados sem baixar arquivo (como preview).
    """
    cmd = [
        "gallery-dl",
        "--ignore-config",
        "--dump-json",
    ]

    if "instagram.com" in req.url:
        cmd += ["--cookies", str(INSTAGRAM_COOKIES)]

    cmd.append(req.url)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print("CMD:", " ".join(cmd))
        print("STDOUT:", proc.stdout)
        print("STDERR:", proc.stderr)

        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or "Erro desconhecido")

        metadata = json.loads(proc.stdout)
        return metadata

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download")
def download(req: DownloadRequest):
    """
    Baixa o conteúdo e retorna como binário (mp4, jpg, zip).
    """
    temp_dir = BASE_TEMP / f"job-{uuid.uuid4()}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Executa o download
        run_gallery_dl(req.url, temp_dir)

        # Só arquivos, nada de diretório
        files = [f for f in temp_dir.glob("**/*") if f.is_file()]

        if not files:
            raise HTTPException(status_code=500, detail="Nenhum arquivo foi baixado.")

        # Se tiver mais de 1 arquivo → ZIP
        if len(files) > 1:
            zip_path = temp_dir / "gallery.zip"
            shutil.make_archive(str(zip_path.with_suffix("")), "zip", temp_dir)
            data = zip_path.read_bytes()

            return Response(
                content=data,
                media_type="application/zip",
                headers={"Content-Disposition": 'attachment; filename="gallery.zip"'}
            )

        # Apenas 1 arquivo → retorna direto
        file = files[0]
        data = file.read_bytes()

        ext = file.suffix.lower()
        mime = {
            ".mp4": "video/mp4",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp"
        }.get(ext, "application/octet-stream")

        return Response(
            content=data,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{file.name}"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
