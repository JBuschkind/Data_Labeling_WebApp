#!/usr/bin/env python3
"""
Hilfsskript zum Überprüfen des Hashs eines Bildes
Verwendung: python check_hash.py <pfad_zum_bild>
"""

import sys
import hashlib
import os

def calculate_file_hash(filepath):
    """Berechnet SHA-256 Hash einer Datei (identisch zur Backend-Funktion)"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            # Erste 64KB lesen
            chunk = f.read(65536)
            hash_sha256.update(chunk)
            # Rest der Datei lesen
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"Fehler beim Berechnen des Hashs: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Verwendung: python check_hash.py <pfad_zum_bild>")
        print("\nBeispiele:")
        print("  python check_hash.py sample_images/bild.jpg")
        print("  python check_hash.py uploads/bild.png")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"Fehler: Datei nicht gefunden: {filepath}")
        sys.exit(1)
    
    if not os.path.isfile(filepath):
        print(f"Fehler: Pfad ist keine Datei: {filepath}")
        sys.exit(1)
    
    print(f"Berechne Hash für: {filepath}")
    image_hash = calculate_file_hash(filepath)
    
    if image_hash:
        print(f"\nHash (SHA-256): {image_hash}")
        print(f"\nURL zum Bild: /api/image/{image_hash}")
    else:
        print("Fehler: Hash konnte nicht berechnet werden")
        sys.exit(1)

if __name__ == '__main__':
    main()

