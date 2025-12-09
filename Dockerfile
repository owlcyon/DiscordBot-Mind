# Use a slim Python base image for smaller size
FROM python:3.12-slim

# Set the working directory to /app (the root of your application inside the container)
WORKDIR /app

# 1. Copy only requirements.txt first (for Docker layer caching optimization)
COPY requirements.txt .

# 2. Install dependencies (This layer is only rebuilt if requirements.txt changes)
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of the application files: bot.py and the entire 'app/' folder
# This is the critical step to ensure app/ is present for imports
COPY . .

# 4. Set the command to run the application
CMD ["python", "bot.py"]