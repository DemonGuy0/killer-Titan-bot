# Usa una imagen base con Python
FROM python:3.13.5

# Define el directorio de trabajo
WORKDIR /app

# Actualiza los paquetes e instala FFmpeg
RUN apt update && apt upgrade -y && \
    apt install -y ffmpeg && \
    apt install -y build-essential &&\
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Create a directory .spotdl
RUN mkdir /.spotdl
RUN chmod -R 777 /.spotdl

# Copia los archivos del proyecto, excluyendo los ignorados en .dockerignore
COPY . /app

# Asegurar que el directorio de trabajo tiene los permisos correctos
RUN chmod -R 777 /app

# Actualiza pip
RUN pip install --upgrade pip

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

# Comando para ejecutar la aplicación
CMD ["python", "bot.py"]
