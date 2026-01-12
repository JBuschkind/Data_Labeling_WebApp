# Data_Labeling_WebApp
This Webapp was made to Label Data for an Image Recognition University Project

## Features

- **Image Upload**: Upload images and annotate them
- **Interactive Drawing**: Click on points that automatically connect
- **Closed Shapes**: The last connection automatically closes the shape and fills it semi-transparently
- **Label Checklist**: Choose from a list of labels or add new ones
- **Automatic Shape Recognition**: Dropdown automatically selects the shape type based on the number of points
- **Manual Adjustment**: Shape type can be manually changed

## Installation with Docker

### Prerequisites

- Docker and Docker Compose installed
- Nginx Proxy Manager is already running (with an external network named `proxy`)

### Setup

1. Clone the repository or copy the files to your server

2. Start the container:
   ```bash
   docker-compose up -d
   ```

4. Make sure the Port 5000 is reachable

## Usage

1. Open the web interface via the configured Proxy Host
2. Click on "Select Image" and upload an image
3. Click on the image to set points
4. The points automatically connect and form a closed shape
5. Select labels from the checklist
6. The shape type is automatically recognized based on the number of points
7. Save the annotation with "Save Annotation"

## Projektstruktur

```
Dataset_Tool/
├── app.py                 # Flask Backend
├── index.html             # Main HTML file
├── static/
│   ├── style.css         # Stylesheet
│   └── script.js         # Frontend logic
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker Compose configuration
├── uploads/              # Uploaded images (will be created)
└── annotations/          # Saved annotations (will be created)
```

## API-Endpunkte

- `GET /` - Hauptseite
- `POST /api/save` - Annotation speichern
- `GET /api/annotations` - Alle Annotationen abrufen

## Development

### With Docker and Auto-Reload

For development with automatic reloading on code changes:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

When changes are made to Python code (`app.py`) or frontend files (`index.html`, `static/*`), Flask automatically reloads.

**Note:** Use `docker-compose.dev.yml` only for development, not for production!

### Local Development without Docker

```bash
pip install -r requirements.txt
python app.py
```

The application will then run on `http://localhost:5000`

### Production vs. Development

- **Production:** `docker-compose.yml` - Code is copied into the image, no auto-reload
- **Development:** `docker-compose.dev.yml` - Code is mounted as a volume, auto-reload enabled

## Customization

### Changing Labels

Edit the `labels` array in `static/script.js`:

```javascript
let labels = ['Person', 'Gruppe', 'Tier', 'Landschaft', 'Portrait', 'Überlappung von Hauptmotiven', 'Bildsymetrie verletzt', 'Nacht', 'Tag'];

```

### Adjusting Shape Types

Edit the `updateShapeType()` function in `static/script.js` or the options in the `select` element in `index.html`.

