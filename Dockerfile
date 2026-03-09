# Dockerfile
# Imagem base Python slim — menor tamanho, sem Pygame (headless)
FROM python:3.11-slim

# Metadados
LABEL maintainer="FIAP Pós-Tech"
LABEL description="VRP Hospitalar RMSP — Algoritmo Genético + FastAPI"

# Evita prompts interativos durante instalação
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias para matplotlib/numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python ANTES do código
# (aproveita cache do Docker se requirements não mudaram)
COPY requirements_api.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements_api.txt \
    && pip install --no-cache-dir \
        fastapi \
        uvicorn[standard] \
        matplotlib \
        numpy \
        requests \
        pillow

# Copia o código do projeto (sem pygame — não usado na API)
COPY benchmark_greater_sp.py .
COPY genetic_algorithm.py .
COPY llm_report.py .
COPY core/ ./core/
COPY domain/ ./domain/
COPY vrp/ ./vrp/
COPY api/ ./api/
COPY tests/ ./tests/
COPY generate_test_report.py .

# Porta exposta pelo uvicorn
EXPOSE 8000

# Healthcheck — Azure usa para saber se o container está saudável
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Comando de inicialização
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
