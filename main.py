from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from starlette.responses import Response
from starlette.datastructures import UploadFile, Headers
from starlette.responses import MultipartResponse
import mimetypes

@app.post("/download")
def download(req: DownloadRequest):
    """
    Retorna TODOS os arquivos como multipart/form-data,
    ideal para n8n (Split Out).
    Sem ZIP, sem base64.
    """
    temp_dir = BASE_TEMP / f"job-{uuid.uuid4()}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Baixa tudo
        run_gallery_dl(req.url, temp_dir)

        files = sorted([f for f in temp_dir.glob("**/*") if f.is_file()])

        if not files:
            raise HTTPException(status_code=500, detail="Nenhum arquivo foi baixado.")

        # Construir partes multipart
        parts = []

        boundary = "X-GALLERY-BOUNDARY"

        body = b""

        for file in files:
            data = file.read_bytes()
            mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"

            body += (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"file\"; filename=\"{file.name}\"\r\n"
                f"Content-Type: {mime}\r\n\r\n"
            ).encode("utf-8") + data + b"\r\n"

        body += f"--{boundary}--\r\n".encode("utf-8")

        return Response(
            content=body,
            media_type=f"multipart/form-data; boundary={boundary}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
