FROM python:3.9-slim

RUN apt-get update && apt-get install -y build-essential libpq-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
WORKDIR /app

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
