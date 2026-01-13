from flask import Flask, request, jsonify, send_from_directory, send_file
import os
import json
import random
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ANNOTATIONS_FOLDER'] = 'annotations'
app.config['SAMPLE_IMAGES_FOLDER'] = 'sample_images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ordner erstellen falls nicht vorhanden
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANNOTATIONS_FOLDER'], exist_ok=True)
os.makedirs(app.config['SAMPLE_IMAGES_FOLDER'], exist_ok=True)

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
        
        # Verwende Dateinamen statt Hash
        filename = data.get('filename')
        
        if filename:
            # Sicherheitsprüfung: Verhindere Path Traversal
            filename = os.path.basename(filename)
            # Speichere nach Dateinamen (überschreibt alte Annotationen für dasselbe Bild)
            annotation_file = os.path.join(
                app.config['ANNOTATIONS_FOLDER'],
                f"annotation_{filename}.json"
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

def get_image_priority(image_filename, annotations_folder):
    """Bestimmt die Priorität eines Bildes für die Auswahl"""
    # Verwende Dateinamen statt Hash
    annotation_file = os.path.join(annotations_folder, f"annotation_{image_filename}.json")
    
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
                        image_files.append((filename, image_path))
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
        selected_filename, selected_image_path = random.choice(image_files)
        
        # Prüfe ob Datei wirklich existiert
        if not os.path.isfile(selected_image_path):
            return jsonify({'error': f'Bilddatei nicht gefunden: {selected_image_path}'}), 404
        
        # URL-encode den Dateinamen für sichere Übertragung
        from urllib.parse import quote
        encoded_filename = quote(selected_filename, safe='')
        
        # Gib JSON mit Dateinamen zurück
        return jsonify({
            'filename': selected_filename,
            'imageUrl': f'/api/image/{encoded_filename}'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/image/<path:filename>', methods=['GET'])
def get_image(filename):
    """Gibt ein Bild anhand des Dateinamens zurück"""
    try:
        # URL-decode den Dateinamen
        from urllib.parse import unquote
        filename = unquote(filename)
        
        # Sicherheitsprüfung: Verhindere Path Traversal
        filename = os.path.basename(filename)
        image_path = os.path.join(app.config['SAMPLE_IMAGES_FOLDER'], filename)
        
        # Prüfe ob Datei existiert
        if not os.path.isfile(image_path):
            return jsonify({'error': f'Bilddatei nicht gefunden: {filename}'}), 404
        
        return send_file(image_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/annotation/<filename>', methods=['GET'])
def get_annotation_by_filename(filename):
    try:
        # Sicherheitsprüfung: Verhindere Path Traversal
        filename = os.path.basename(filename)
        annotation_file = os.path.join(
            app.config['ANNOTATIONS_FOLDER'],
            f"annotation_{filename}.json"
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

