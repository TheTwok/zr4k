FROM python:3.10-slim
WORKDIR /usr/src/app

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code and the plain Telegram bot interface
COPY backend/ ./backend/
COPY plain_bot/ ./plain_bot/

# Ensure the persistent data directory exists and is writable
USER root
RUN mkdir -p /app/data && chmod 777 /app/data

# Command to launch the plain bot, parser, scheduler, and health server
CMD ["python", "-m", "plain_bot.main"]
