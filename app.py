from flask import Flask, request, jsonify, send_from_directory, send_file
from flask.helpers import make_response
import os
import json
import random
import hashlib
from datetime import datetime

app = Flask(__name__)

# CORS Headers hinzufügen (falls nötig)
@app.after_request
def after_request(response):
    """Fügt CORS-Header zu allen Responses hinzu"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ANNOTATIONS_FOLDER'] = 'annotations'
app.config['SAMPLE_IMAGES_FOLDER'] = 'sample_images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Cache für Bild-Hashes (Dateiname -> Hash)
_image_hash_cache = {}
_hash_cache_file = 'image_hash_cache.json'

# Mapping von Hash zu Bildpfad (für schnellen Zugriff)
_hash_to_path_cache = {}
_hash_to_path_file = 'hash_to_path_cache.json'

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

def load_hash_to_path_cache():
    """Lädt das Hash-zu-Pfad-Mapping aus einer Datei"""
    global _hash_to_path_cache
    cache_file = os.path.join(app.config['ANNOTATIONS_FOLDER'], '..', _hash_to_path_file)
    cache_file = os.path.abspath(cache_file)
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                _hash_to_path_cache = json.load(f)
        except Exception:
            _hash_to_path_cache = {}
    else:
        _hash_to_path_cache = {}

def save_hash_to_path_cache():
    """Speichert das Hash-zu-Pfad-Mapping in eine Datei"""
    global _hash_to_path_cache
    cache_file = os.path.join(app.config['ANNOTATIONS_FOLDER'], '..', _hash_to_path_file)
    cache_file = os.path.abspath(cache_file)
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(_hash_to_path_cache, f, indent=2)
    except Exception:
        pass

# Ordner erstellen falls nicht vorhanden
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANNOTATIONS_FOLDER'], exist_ok=True)
os.makedirs(app.config['SAMPLE_IMAGES_FOLDER'], exist_ok=True)

# Hash-Cache laden beim Start
load_hash_cache()
load_hash_to_path_cache()

def index_all_images():
    """Indiziert alle Bilder beim Start für schnelleren Zugriff"""
    print("Indiziere Bilder...")
    indexed = 0
    search_folders = [
        app.config['SAMPLE_IMAGES_FOLDER'],
        app.config['UPLOAD_FOLDER']
    ]
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    for folder in search_folders:
        if not os.path.exists(folder):
            continue
        
        try:
            for filename in os.listdir(folder):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in image_extensions:
                    image_path = os.path.join(folder, filename)
                    if os.path.isfile(image_path):
                        image_hash = calculate_file_hash(image_path)
                        if image_hash and image_hash not in _hash_to_path_cache:
                            _hash_to_path_cache[image_hash] = image_path
                            indexed += 1
        except Exception as e:
            print(f"Fehler beim Indizieren von {folder}: {e}")
    
    if indexed > 0:
        save_hash_to_path_cache()
        print(f"{indexed} Bilder indiziert")
    else:
        print("Keine neuen Bilder zum Indizieren gefunden")

# Indiziere alle Bilder beim Start (im Hintergrund, blockiert nicht)
import threading
threading.Thread(target=index_all_images, daemon=True).start()

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
        
        # Hash berechnen und in Cache speichern
        image_hash = calculate_file_hash(selected_image_path)
        if image_hash:
            _hash_to_path_cache[image_hash] = selected_image_path
            save_hash_to_path_cache()
        
        # Bild als Blob senden, aber Hash in Header mitgeben
        response = send_file(selected_image_path)
        if image_hash:
            response.headers['X-Image-Hash'] = image_hash
        return response
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/image/<image_hash>', methods=['GET'])
def get_image_by_hash(image_hash):
    """Gibt ein Bild basierend auf seinem Hash zurück"""
    try:
        # Prüfe zuerst im Cache
        if image_hash in _hash_to_path_cache:
            image_path = _hash_to_path_cache[image_hash]
            if os.path.exists(image_path) and os.path.isfile(image_path):
                # Verifiziere, dass der Hash noch stimmt (Datei könnte sich geändert haben)
                current_hash = calculate_file_hash(image_path)
                if current_hash == image_hash:
                    return send_file(image_path)
                else:
                    # Hash stimmt nicht mehr, entferne aus Cache
                    del _hash_to_path_cache[image_hash]
                    save_hash_to_path_cache()
        
        # Verwende die gemeinsame Suchfunktion
        image_path = find_image_by_hash(image_hash)
        if image_path:
            return send_file(image_path)
        
        # Wenn immer noch nicht gefunden, prüfe ob Annotation existiert (für Debugging)
        annotation_file = os.path.join(
            app.config['ANNOTATIONS_FOLDER'],
            f"annotation_{image_hash}.json"
        )
        if os.path.exists(annotation_file):
            return jsonify({
                'error': 'Bild nicht gefunden',
                'message': f'Annotation existiert für Hash {image_hash}, aber Bilddatei wurde nicht gefunden. Möglicherweise wurde das Bild gelöscht oder verschoben.',
                'hash': image_hash
            }), 404
        
        return jsonify({
            'error': 'Bild nicht gefunden',
            'message': f'Kein Bild mit Hash {image_hash} gefunden',
            'hash': image_hash
        }), 404
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/file-hash', methods=['GET'])
def get_file_hash():
    """Gibt den Hash einer Bilddatei zurück (anhand des Dateinamens)"""
    try:
        filename = request.args.get('filename')
        folder = request.args.get('folder', 'sample_images')  # 'sample_images' oder 'uploads'
        
        if not filename:
            return jsonify({'error': 'Parameter "filename" fehlt'}), 400
        
        # Bestimme den Ordner
        if folder == 'uploads':
            search_folder = app.config['UPLOAD_FOLDER']
        else:
            search_folder = app.config['SAMPLE_IMAGES_FOLDER']
        
        # Suche die Datei
        filepath = os.path.join(search_folder, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'error': 'Datei nicht gefunden',
                'filename': filename,
                'folder': folder,
                'searched_path': filepath
            }), 404
        
        if not os.path.isfile(filepath):
            return jsonify({'error': 'Pfad ist keine Datei'}), 400
        
        # Berechne Hash
        image_hash = calculate_file_hash(filepath)
        
        if not image_hash:
            return jsonify({'error': 'Hash konnte nicht berechnet werden'}), 500
        
        return jsonify({
            'success': True,
            'filename': filename,
            'folder': folder,
            'filepath': filepath,
            'hash': image_hash
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/list-images', methods=['GET'])
def list_images():
    """Listet alle Bilder mit ihren Hashes auf"""
    try:
        folder = request.args.get('folder', 'sample_images')  # 'sample_images' oder 'uploads'
        
        # Bestimme den Ordner
        if folder == 'uploads':
            search_folder = app.config['UPLOAD_FOLDER']
        else:
            search_folder = app.config['SAMPLE_IMAGES_FOLDER']
        
        if not os.path.exists(search_folder):
            return jsonify({
                'error': 'Ordner existiert nicht',
                'folder': folder,
                'path': search_folder
            }), 404
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        images = []
        
        try:
            for filename in os.listdir(search_folder):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in image_extensions:
                    image_path = os.path.join(search_folder, filename)
                    if os.path.isfile(image_path):
                        image_hash = calculate_file_hash(image_path)
                        images.append({
                            'filename': filename,
                            'hash': image_hash,
                            'path': image_path
                        })
        except Exception as e:
            return jsonify({'error': f'Fehler beim Lesen des Ordners: {str(e)}'}), 500
        
        return jsonify({
            'success': True,
            'folder': folder,
            'path': search_folder,
            'count': len(images),
            'images': images
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Lädt ein Bild hoch und speichert es mit Hash-Referenz"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Keine Datei hochgeladen'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400
        
        # Speichere Datei temporär
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Berechne Hash
        image_hash = calculate_file_hash(filepath)
        if image_hash:
            # In Cache speichern
            _hash_to_path_cache[image_hash] = filepath
            save_hash_to_path_cache()
        
        return jsonify({
            'success': True,
            'hash': image_hash,
            'message': 'Bild erfolgreich hochgeladen'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def find_image_by_hash(image_hash):
    """Sucht ein Bild anhand seines Hashs und speichert es im Cache"""
    # Prüfe zuerst im Cache
    if image_hash in _hash_to_path_cache:
        image_path = _hash_to_path_cache[image_hash]
        if os.path.exists(image_path) and os.path.isfile(image_path):
            return image_path
    
    # Suche in allen Ordnern
    search_folders = [
        app.config['SAMPLE_IMAGES_FOLDER'],
        app.config['UPLOAD_FOLDER']
    ]
    
    for folder in search_folders:
        if not os.path.exists(folder):
            continue
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        try:
            for filename in os.listdir(folder):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in image_extensions:
                    image_path = os.path.join(folder, filename)
                    if os.path.isfile(image_path):
                        file_hash = calculate_file_hash(image_path)
                        if file_hash == image_hash:
                            # In Cache speichern
                            _hash_to_path_cache[image_hash] = image_path
                            save_hash_to_path_cache()
                            return image_path
        except Exception:
            continue
    
    return None

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
            
            # Versuche Bild zu finden und im Cache zu speichern (für späteren Zugriff)
            find_image_by_hash(image_hash)
            
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

