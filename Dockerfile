# Use a lightweight, stable Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install dependencies first (faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . .

# MANDATE 3.3: Set the command to run the stateless bot worker
CMD ["python", "bot.py"] 
