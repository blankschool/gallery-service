FROM python:3.12-slim

WORKDIR /app

RUN apt update && apt install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia o app
COPY main.py ./main.py
# copia o cookie
COPY instagram.txt ./instagram.txt

EXPOSE 8003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
