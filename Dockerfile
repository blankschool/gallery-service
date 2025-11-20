FROM python:3.11-slim

# Dependências necessárias
RUN apt update && apt install -y ffmpeg wget git && apt clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
