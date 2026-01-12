FROM python:3.11-slim

WORKDIR /app

# System-Abhängigkeiten installieren
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendung kopieren
COPY . .

# Ordner für Uploads, Annotations und Sample Images erstellen
RUN mkdir -p uploads annotations sample_images

# Port freigeben
EXPOSE 5000

# Anwendung starten
CMD ["python", "app.py"]

