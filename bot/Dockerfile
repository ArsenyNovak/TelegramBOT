FROM python:3.11-slim
RUN groupadd -r groupbot && useradd -r -g groupbot userbot

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
WORKDIR /app/Telegram_bot
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

USER userbot