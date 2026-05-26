FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN mkdir -p /app/database

ENV HOST=0.0.0.0
ENV PORT=8080
ENV DATABASE_DIR=/app/database
ENV DATABASE_PATH=/app/database/hexacare.sqlite3

EXPOSE 8080

CMD ["python3", "app.py"]
