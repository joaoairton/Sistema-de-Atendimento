#!/bin/sh

echo "Aguardando banco de dados..."
sleep 30

poetry run alembic upgrade head

sleep 30

poetry run uvicorn app.app:app --host 0.0.0.0 --port 8000