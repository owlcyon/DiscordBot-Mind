# Dockerfile (For Building the Bot Application)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Command to run the bot when deployed to Railway/Cloud Run
CMD ["python", "bot.py"]
