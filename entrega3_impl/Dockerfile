# Dockerfile — Sistema de Atendimento Entrega 3
FROM python:3.12-slim

WORKDIR /app

# Instala dependências do sistema (lxml precisa de libxml2)
RUN apt-get update && apt-get install -y \
    libxml2-dev libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto
COPY . .

# Cria pastas de XMLs
RUN mkdir -p xml_gerados xml_entrada

EXPOSE 5002

CMD ["python", "app.py"]
