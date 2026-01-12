# Nginx Proxy Manager Konfiguration

## Standard-Konfiguration

Die Standard-Konfiguration sollte für die meisten Fälle ausreichen. Wenn Sie die App bereits über Nginx Proxy Manager laufen haben, sollten die neuen API-Endpoints automatisch funktionieren.

## Überprüfung der Proxy-Konfiguration

### 1. Proxy Host Einstellungen

In Nginx Proxy Manager sollten folgende Einstellungen gesetzt sein:

- **Forward Hostname/IP**: `image-annotation-tool` (Container-Name)
- **Forward Port**: `5000`
- **Forward Scheme**: `http`
- **Block Common Exploits**: Aktiviert (empfohlen)
- **Websockets Support**: Nicht erforderlich für diese App

### 2. Custom Headers (Optional, aber empfohlen)

Falls Sie Custom Headers weitergeben müssen, fügen Sie diese in den "Advanced" Tab ein:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

Diese sind normalerweise bereits standardmäßig gesetzt.

### 3. Timeouts für große Dateien

Falls Sie Probleme beim Hochladen großer Bilder haben, fügen Sie in den "Advanced" Tab ein:

```nginx
proxy_read_timeout 300s;
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
client_max_body_size 20M;
```

### 4. Buffering (Optional)

Für bessere Performance können Sie Buffering deaktivieren:

```nginx
proxy_buffering off;
proxy_request_buffering off;
```

## Neue API-Endpoints

Die folgenden neuen Endpoints sollten ohne zusätzliche Konfiguration funktionieren:

- `GET /api/file-hash?filename=<name>&folder=<sample_images|uploads>`
- `GET /api/list-images?folder=<sample_images|uploads>`
- `GET /api/image/<hash>` (bereits vorhanden)

## Troubleshooting

### Problem: API-Endpoints geben 404 zurück

**Lösung**: 
1. Stellen Sie sicher, dass der Container läuft: `docker ps`
2. Prüfen Sie die Logs: `docker logs image-annotation-tool`
3. Testen Sie direkt auf Port 5000: `http://<server-ip>:5000/api/file-hash?filename=test.jpg`

### Problem: CORS-Fehler im Browser

**Lösung**: 
Die App hat bereits CORS-Header integriert. Falls dennoch Probleme auftreten:
1. Prüfen Sie die Browser-Konsole auf Fehlermeldungen
2. Stellen Sie sicher, dass Sie die richtige Domain verwenden (nicht localhost, wenn die App auf einem Server läuft)

### Problem: Timeout bei großen Dateien

**Lösung**: 
Fügen Sie die Timeout-Einstellungen aus Punkt 3 oben hinzu.

### Problem: Custom Headers werden nicht weitergegeben

**Lösung**: 
Die App verwendet den `X-Image-Hash` Header. Dieser sollte automatisch funktionieren. Falls nicht:
1. Prüfen Sie, ob "Preserve Host" deaktiviert ist
2. Stellen Sie sicher, dass Custom Headers in NPM nicht überschrieben werden

## Test der Konfiguration

Testen Sie die Endpoints direkt:

```bash
# Hash einer Datei abrufen
curl "https://ihre-domain.de/api/file-hash?filename=bild.jpg&folder=sample_images"

# Alle Bilder auflisten
curl "https://ihre-domain.de/api/list-images?folder=sample_images"

# Bild per Hash abrufen
curl "https://ihre-domain.de/api/image/<hash>"
```

## SSL-Zertifikat

Stellen Sie sicher, dass SSL aktiviert ist:
- **SSL Certificate**: Wählen Sie ein gültiges Zertifikat aus
- **Force SSL**: Aktiviert (empfohlen)
- **HTTP/2 Support**: Aktiviert (empfohlen)

