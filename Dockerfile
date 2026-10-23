# Usa una imagen base slim con Python (versión estable)
FROM python:3.11-slim

# Define el directorio de trabajo
WORKDIR /app

# Actualiza los paquetes e instala dependencias del sistema
RUN apt update && apt upgrade -y && \
    apt install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Create .spotdl directory with proper permissions
RUN mkdir /.spotdl && chmod -R 777 /.spotdl

# Copia solo requirements primero para mejor caché
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -U -r requirements.txt

# Copia los archivos del proyecto
COPY . .

# Asegurar permisos
RUN chmod -R 777 /app

EXPOSE 7860

# Comando para ejecutar la aplicación
CMD ["python", "bot.py"]
