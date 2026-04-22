FROM python:3.12-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar glpk-utils
RUN apt-get update \
    && apt-get install -y -qq glpk-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero (mejor para cache)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Cambiar cwd a src
WORKDIR /app/src

# Comando por defecto
ENTRYPOINT ["python", "main.py"]