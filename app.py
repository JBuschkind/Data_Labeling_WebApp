from flask import Flask, request, jsonify, send_from_directory, send_file
import os
import json
import random
import hashlib
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ANNOTATIONS_FOLDER'] = 'annotations'
app.config['SAMPLE_IMAGES_FOLDER'] = 'sample_images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Cache für Bild-Hashes (Dateiname -> Hash)
_image_hash_cache = {}
_hash_cache_file = 'image_hash_cache.json'

def load_hash_cache():
    """Lädt den Hash-Cache aus einer Datei"""
    global _image_hash_cache
    cache_file = os.path.join(app.config['ANNOTATIONS_FOLDER'], '..', _hash_cache_file)
    cache_file = os.path.abspath(cache_file)
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                _image_hash_cache = json.load(f)
        except Exception:
            _image_hash_cache = {}
    else:
        _image_hash_cache = {}

def save_hash_cache():
    """Speichert den Hash-Cache in eine Datei"""
    global _image_hash_cache
    cache_file = os.path.join(app.config['ANNOTATIONS_FOLDER'], '..', _hash_cache_file)
    cache_file = os.path.abspath(cache_file)
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(_image_hash_cache, f, indent=2)
    except Exception:
        pass

# Ordner erstellen falls nicht vorhanden
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANNOTATIONS_FOLDER'], exist_ok=True)
os.makedirs(app.config['SAMPLE_IMAGES_FOLDER'], exist_ok=True)

# Hash-Cache laden beim Start
load_hash_cache()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    response = send_from_directory('static', filename)
    # Cache-Control Header setzen, um Browser-Caching zu verhindern
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/save', methods=['POST'])
def save_annotation():
    try:
        data = request.json
        
        # Wenn ein imageHash vorhanden ist, speichere nach Hash (überschreibt alte Annotation)
        image_hash = data.get('imageHash')
        
        if image_hash:
            # Speichere nach Hash (überschreibt alte Annotationen für dasselbe Bild)
            annotation_file = os.path.join(
                app.config['ANNOTATIONS_FOLDER'],
                f"annotation_{image_hash}.json"
            )
            
            # Wenn bereits eine Annotation existiert, behalte reviewCount
            if os.path.exists(annotation_file):
                with open(annotation_file, 'r', encoding='utf-8') as f:
                    existing_annotation = json.load(f)
                    # Behalte reviewCount und lastReviewed wenn vorhanden
                    data['reviewCount'] = existing_annotation.get('reviewCount', 0)
                    data['lastReviewed'] = existing_annotation.get('lastReviewed')
        else:
            # Fallback: Speichere mit Timestamp
            annotation_file = os.path.join(
                app.config['ANNOTATIONS_FOLDER'],
                f"annotation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        
        # Stelle sicher, dass reviewCount gesetzt ist
        if 'reviewCount' not in data:
            data['reviewCount'] = 0
        
        with open(annotation_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True, 'message': 'Annotation gespeichert'}), 200
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/annotations', methods=['GET'])
def get_annotations():
    try:
        annotations = []
        for filename in os.listdir(app.config['ANNOTATIONS_FOLDER']):
            if filename.endswith('.json'):
                filepath = os.path.join(app.config['ANNOTATIONS_FOLDER'], filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    annotations.append(json.load(f))
        
        return jsonify({'annotations': annotations}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def calculate_file_hash(filepath, use_cache=True):
    """Berechnet SHA-256 Hash einer Datei (mit Caching)"""
    # Prüfe Cache zuerst
    filename = os.path.basename(filepath)
    file_stat = os.stat(filepath)
    cache_key = f"{filename}_{file_stat.st_mtime}_{file_stat.st_size}"
    
    if use_cache and cache_key in _image_hash_cache:
        return _image_hash_cache[cache_key]
    
    # Hash berechnen
    hash_sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            # Nur ersten Teil lesen für schnellere Berechnung (erste 64KB)
            # Das ist ausreichend für eindeutige Identifikation
            chunk = f.read(65536)
            hash_sha256.update(chunk)
            # Rest der Datei auch lesen für vollständigen Hash
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        hash_value = hash_sha256.hexdigest()
        
        # In Cache speichern
        if use_cache:
            _image_hash_cache[cache_key] = hash_value
            save_hash_cache()
        
        return hash_value
    except Exception:
        return None

def get_image_priority(image_path, annotations_folder):
    """Bestimmt die Priorität eines Bildes für die Auswahl"""
    image_hash = calculate_file_hash(image_path)
    if not image_hash:
        return (2, 999999)  # Niedrigste Priorität wenn Hash nicht berechnet werden kann
    
    annotation_file = os.path.join(annotations_folder, f"annotation_{image_hash}.json")
    
    if not os.path.exists(annotation_file):
        # Keine Annotation vorhanden - höchste Priorität
        return (0, 0)
    
    try:
        with open(annotation_file, 'r', encoding='utf-8') as f:
            annotation = json.load(f)
        
        # Anzahl Überprüfungen (reviewCount) oder 0 wenn nicht vorhanden
        review_count = annotation.get('reviewCount', 0)
        
        # Priorität: 1 = hat Annotation, dann nach reviewCount sortiert
        return (1, review_count)
    except Exception:
        # Fehler beim Lesen - behandle als nicht annotiert
        return (0, 0)

@app.route('/api/random-image', methods=['GET'])
def get_random_image():
    try:
        sample_folder = app.config['SAMPLE_IMAGES_FOLDER']
        
        # Prüfe ob Ordner existiert
        if not os.path.exists(sample_folder):
            return jsonify({'error': f'Ordner {sample_folder} existiert nicht'}), 404
        
        # Unterstützte Bildformate
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        
        # Alle Bilddateien im Ordner finden
        image_files = []
        try:
            all_files = os.listdir(sample_folder)
            for filename in all_files:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in image_extensions:
                    image_path = os.path.join(sample_folder, filename)
                    # Prüfe ob Datei wirklich existiert
                    if os.path.isfile(image_path):
                        image_files.append(image_path)
        except Exception as e:
            return jsonify({'error': f'Fehler beim Lesen des Ordners: {str(e)}'}), 500
        
        if not image_files:
            # Debug-Informationen
            all_files = os.listdir(sample_folder) if os.path.exists(sample_folder) else []
            return jsonify({
                'error': f'Keine Bilder im sample_images Ordner gefunden. Gefundene Dateien: {all_files[:10]}',
                'folder': sample_folder,
                'files_count': len(all_files)
            }), 404
        
        # Einfach ein zufälliges Bild zurückgeben - SOFORT, ohne Hash-Berechnung
        # Die Priorisierung kann später im Hintergrund passieren
        selected_image_path = random.choice(image_files)
        
        # Prüfe ob Datei wirklich existiert
        if not os.path.isfile(selected_image_path):
            return jsonify({'error': f'Bilddatei nicht gefunden: {selected_image_path}'}), 404
        
        return send_file(selected_image_path)
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/annotation/<image_hash>', methods=['GET'])
def get_annotation_by_hash(image_hash):
    try:
        annotation_file = os.path.join(
            app.config['ANNOTATIONS_FOLDER'],
            f"annotation_{image_hash}.json"
        )
        
        if os.path.exists(annotation_file):
            with open(annotation_file, 'r', encoding='utf-8') as f:
                annotation = json.load(f)
            
            # Erhöhe Überprüfungszähler beim Laden
            review_count = annotation.get('reviewCount', 0)
            annotation['reviewCount'] = review_count + 1
            annotation['lastReviewed'] = datetime.now().isoformat()
            
            # Speichere aktualisierte Annotation
            with open(annotation_file, 'w', encoding='utf-8') as f:
                json.dump(annotation, f, indent=2, ensure_ascii=False)
            
            return jsonify(annotation), 200
        else:
            return jsonify({'error': 'Annotation nicht gefunden'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Debug-Modus basierend auf Umgebungsvariable
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)

