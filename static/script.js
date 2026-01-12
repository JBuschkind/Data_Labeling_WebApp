// Canvas und Kontext
console.log('Script.js wird geladen...');
const canvas = document.getElementById('annotationCanvas');
let ctx = null;
if (!canvas) {
    console.error('Canvas-Element nicht gefunden!');
} else {
    console.log('Canvas-Element gefunden');
    ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('Kontext konnte nicht erstellt werden!');
    }
}

// ============================================
// KONFIGURATION - HIER KÖNNEN SIE ANPASSEN
// ============================================

// Labels: Hier können Sie die Standard-Labels ändern
// Sie können auch neue Labels über die UI hinzufügen
const DEFAULT_LABELS = ['Person', 'Gruppe', 'Tier', 'Landschaft', 'Portrait', 'Überlappung von Hauptmotiven', 'Bildsymetrie verletzt', 'Nacht', 'Tag'];

// Form-Typ-Mapping: Hier können Sie die Zuordnung von Punktanzahl zu Form-Typ anpassen
// Format: { anzahlPunkte: { value: 'form-typ-wert', label: 'Anzeigename' } }
const SHAPE_TYPE_MAPPING = {
    0: { value: 'thirds', label: 'Rule of Thirds' },
    1: { value: 'point', label: 'Punkt' },
    2: { value: 'horizon', label: 'Horizont' },
    3: { value: 'triangle', label: 'Dreieck' },
    4: { value: 'rectangle', label: 'Rechteck' },
    5: { value: 'pentagon', label: 'Fünfeck' },
    6: { value: 'hexagon', label: 'Sechseck' },
    7: { value: 'polygon', label: 'Polygon' },
    8: { value: 'polygon', label: 'Polygon' },
    9: { value: 'polygon', label: 'Polygon' },
    10: { value: 'polygon', label: 'Polygon' }
    // Für mehr als 10 Punkte wird automatisch 'polygon' verwendet
};

// ============================================

// Hilfsfunktion: Hash eines Bildes berechnen
async function calculateImageHash(imageData) {
    // Verwende die SubtleCrypto API für Hash-Berechnung
    const encoder = new TextEncoder();
    const data = encoder.encode(imageData);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
}

// Hilfsfunktion: Hash aus Bild-URL oder File berechnen
async function getImageHash(img) {
    try {
        // Erstelle einen Canvas, um die Bilddaten zu bekommen
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = img.width;
        tempCanvas.height = img.height;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(img, 0, 0);
        
        // Konvertiere zu Data URL und berechne Hash
        const imageData = tempCanvas.toDataURL();
        return await calculateImageHash(imageData);
    } catch (error) {
        console.error('Fehler beim Berechnen des Bild-Hashes:', error);
        // Fallback: Verwende Timestamp als Hash
        return `fallback_${Date.now()}`;
    }
}

// Zustand
let subjectPoints = []; // Punkte für Hauptsubjekt-Markierung
let compositionPoints = []; // Punkte für Kompositions-Markierung
let currentMode = 'subject'; // 'subject' oder 'composition'
let currentImage = null;
let imageLoaded = false;
let labels = [...DEFAULT_LABELS]; // Kopie der Standard-Labels
let selectedLabels = new Set();
let currentImageHash = null; // Hash des aktuellen Bildes für Identifikation
let isAutoMode = true; // Verfolgt, ob automatischer Modus aktiv ist

// Farben für die verschiedenen Modi
const SUBJECT_COLOR = '#e74c3c'; // Rot für Subjekt
const COMPOSITION_COLOR = '#3498db'; // Blau für Komposition

// Initialisierung - warte bis DOM geladen ist
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    // DOM ist bereits geladen
    init();
}

function init() {
    console.log('=== Initialisierung gestartet ===');
    console.log('Prüfe ob Button existiert:', document.getElementById('subjectModeBtn'));
    setupEventListeners();
    loadLabels();
    // Setze Standardwert auf Rule of Thirds (0 Punkte)
    const shapeTypeSelect = document.getElementById('shapeType');
    if (shapeTypeSelect) {
        shapeTypeSelect.value = 'thirds';
        updateShapeType();
    } else {
        console.error('shapeType Select nicht gefunden!');
    }
    // Initialisiere Modus-Button (muss nach setupEventListeners sein)
    updateModeButton();
    // Lade automatisch ein zufälliges Bild beim Start
    // Kleine Verzögerung, um sicherzustellen, dass alles initialisiert ist
    console.log('Starte automatisches Laden eines zufälligen Bildes...');
    setTimeout(() => {
        loadRandomImage();
    }, 200);
    console.log('=== Initialisierung abgeschlossen ===');
}

function setupEventListeners() {
    // Bild-Upload
    const imageInput = document.getElementById('imageInput');
    if (imageInput) {
        imageInput.addEventListener('change', handleImageUpload);
    } else {
        console.error('imageInput nicht gefunden!');
    }
    
    const randomImageBtn = document.getElementById('randomImageBtn');
    if (randomImageBtn) {
        randomImageBtn.addEventListener('click', loadRandomImage);
    } else {
        console.error('randomImageBtn nicht gefunden!');
    }
    
    // Canvas-Klicks
    if (canvas) {
        canvas.addEventListener('click', handleCanvasClick);
    } else {
        console.error('Canvas nicht gefunden!');
    }
    
    // Buttons
    const subjectBtn = document.getElementById('subjectModeBtn');
    if (subjectBtn) {
        console.log('Subject-Button gefunden, Event-Listener wird registriert');
        subjectBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Button wurde geklickt!');
            switchToSubjectMode();
        });
    } else {
        console.error('Subject-Button NICHT gefunden!');
    }
    
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearDrawing);
    } else {
        console.error('clearBtn nicht gefunden!');
    }
    
    const undoBtn = document.getElementById('undoBtn');
    if (undoBtn) {
        undoBtn.addEventListener('click', removeLastPoint);
    } else {
        console.error('undoBtn nicht gefunden!');
    }
    
    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveAnnotation);
    } else {
        console.error('saveBtn nicht gefunden!');
    }
    
    // Label-Management
    const addLabelBtn = document.getElementById('addLabelBtn');
    if (addLabelBtn) {
        addLabelBtn.addEventListener('click', addNewLabel);
    } else {
        console.error('addLabelBtn nicht gefunden!');
    }
    
    const newLabelInput = document.getElementById('newLabelInput');
    if (newLabelInput) {
        newLabelInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                addNewLabel();
            }
        });
    } else {
        console.error('newLabelInput nicht gefunden!');
    }
    
    // Shape-Typ Dropdown
    const shapeType = document.getElementById('shapeType');
    if (shapeType) {
        shapeType.addEventListener('change', (e) => {
            // Wenn der Benutzer manuell einen Wert ändert, deaktiviere Auto-Modus
            const expectedValue = getExpectedShapeType(compositionPoints.length);
            if (e.target.value !== expectedValue) {
                isAutoMode = false;
            } else {
                isAutoMode = true;
            }
            drawCanvas();
        });
    } else {
        console.error('shapeType nicht gefunden!');
    }
}

async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
        // Lade Bild zuerst auf Server hoch
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadResponse = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            const errorData = await uploadResponse.json();
            alert(`Fehler beim Hochladen: ${errorData.error || 'Unbekannter Fehler'}`);
            return;
        }
        
        const uploadData = await uploadResponse.json();
        const imageHash = uploadData.hash;
        
        if (!imageHash) {
            alert('Fehler: Bild-Hash konnte nicht ermittelt werden.');
            return;
        }
        
        // Lade Bild mit Hash-basierter URL
        const imageUrl = `/api/image/${imageHash}`;
        const img = new Image();
        img.onload = async () => {
            currentImage = img;
            imageLoaded = true;
            currentImageHash = imageHash;
            
            // Zurücksetzen der Punkte und Modi
            subjectPoints = [];
            compositionPoints = [];
            currentMode = 'subject';
            updateModeButton();
            
            // Canvas-Größe anpassen
            const maxWidth = window.innerWidth - 400; // Platz für Sidebar
            const maxHeight = window.innerHeight - 150; // Platz für Toolbar
            
            let width = img.width;
            let height = img.height;
            
            const scale = Math.min(maxWidth / width, maxHeight / height, 1);
            width *= scale;
            height *= scale;
            
            canvas.width = width;
            canvas.height = height;
            
            // Versuche vorhandene Annotationen zu laden
            await loadExistingAnnotation();
            
            drawCanvas();
            updatePointCount();
            updateShapeType();
        };
        img.onerror = (e) => {
            console.error('Fehler beim Laden des hochgeladenen Bildes:', e);
            alert('Fehler beim Anzeigen des hochgeladenen Bildes.');
        };
        img.src = imageUrl;
    } catch (error) {
        console.error('Fehler beim Hochladen:', error);
        alert(`Fehler beim Hochladen des Bildes: ${error.message}`);
    }
}

function handleCanvasClick(event) {
    if (!imageLoaded) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    if (currentMode === 'subject') {
        subjectPoints.push({ x, y });
    } else {
        compositionPoints.push({ x, y });
    }
    
    drawCanvas();
    updatePointCount();
    updateShapeType();
}

function switchToSubjectMode() {
    console.log('switchToSubjectMode aufgerufen, aktueller Modus:', currentMode);
    // Toggle zwischen den Modi
    if (currentMode === 'subject') {
        currentMode = 'composition';
        console.log('Wechsel zu Kompositions-Modus');
    } else {
        currentMode = 'subject';
        console.log('Wechsel zu Subjekt-Modus');
    }
    updateModeButton();
    // Zeige visuelles Feedback
    if (imageLoaded) {
        drawCanvas();
    }
}

function updateModeButton() {
    const btn = document.getElementById('subjectModeBtn');
    if (!btn) {
        console.error('Button subjectModeBtn nicht gefunden!');
        return;
    }
    
    if (currentMode === 'subject') {
        btn.textContent = 'Subjekt markieren (aktiv)';
        btn.classList.add('active');
        if (imageLoaded) {
            canvas.style.cursor = 'crosshair';
            canvas.title = 'Subjekt markieren (Rot) - Klicken Sie auf das Bild';
        }
    } else {
        btn.textContent = 'Komposition zeichnen (aktiv)';
        btn.classList.remove('active');
        if (imageLoaded) {
            canvas.style.cursor = 'crosshair';
            canvas.title = 'Komposition zeichnen (Blau) - Klicken Sie auf das Bild';
        }
    }
    console.log('Button aktualisiert, Modus:', currentMode);
}

function drawCanvas() {
    if (!imageLoaded || !ctx || !canvas) {
        console.warn('drawCanvas: imageLoaded=', imageLoaded, 'ctx=', ctx, 'canvas=', canvas);
        return;
    }
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Bild zeichnen
    ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);
    
    // Subjekt-Punkte zeichnen (rot)
    if (subjectPoints.length > 0) {
        drawShape(subjectPoints, SUBJECT_COLOR, 'S');
    }
    
    // Kompositions-Punkte zeichnen (blau)
    if (compositionPoints.length > 0) {
        drawShape(compositionPoints, COMPOSITION_COLOR, 'K');
    }
}

function drawShape(pointsArray, color, labelPrefix) {
    if (pointsArray.length === 0) return;
    
    // Konvertiere Hex-Farbe zu RGBA für Füllung
    let fillColor;
    if (color.startsWith('#')) {
        // Hex zu RGB konvertieren
        const r = parseInt(color.slice(1, 3), 16);
        const g = parseInt(color.slice(3, 5), 16);
        const b = parseInt(color.slice(5, 7), 16);
        fillColor = `rgba(${r}, ${g}, ${b}, 0.3)`;
    } else {
        fillColor = color.replace(')', ', 0.3)').replace('rgb', 'rgba');
    }
    
    // Punkte verbinden
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.fillStyle = fillColor;
    
    ctx.beginPath();
    ctx.moveTo(pointsArray[0].x, pointsArray[0].y);
    
    for (let i = 1; i < pointsArray.length; i++) {
        ctx.lineTo(pointsArray[i].x, pointsArray[i].y);
    }
    
    // Form zeichnen basierend auf Punktanzahl
    if (pointsArray.length === 1) {
        // Einzelner Punkt - nur Punkt zeichnen, keine Linie
        ctx.closePath();
    } else if (pointsArray.length === 2) {
        // Horizont - Linie zwischen zwei Punkten
        ctx.stroke();
    } else {
        // 3+ Punkte - geschlossene Form mit Füllung
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
    }
    
    // Punkte zeichnen
    ctx.fillStyle = color;
    pointsArray.forEach((point, index) => {
        ctx.beginPath();
        ctx.arc(point.x, point.y, 6, 0, Math.PI * 2);
        ctx.fill();
        
        // Punktnummer mit Label-Präfix anzeigen
        ctx.fillStyle = '#fff';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${labelPrefix}${index + 1}`, point.x, point.y);
        ctx.fillStyle = color;
    });
}

function clearDrawing() {
    // Lösche nur die Punkte des aktuellen Modus
    if (currentMode === 'subject') {
        subjectPoints = [];
    } else {
        compositionPoints = [];
    }
    isAutoMode = true; // Zurücksetzen auf Auto-Modus
    drawCanvas();
    updatePointCount();
    updateShapeType(); // Setzt automatisch auf 'thirds' zurück wenn keine Kompositions-Punkte mehr vorhanden
}

function removeLastPoint() {
    if (currentMode === 'composition' && compositionPoints.length > 0) {
        compositionPoints.pop();
    } else if (currentMode === 'subject' && subjectPoints.length > 0) {
        subjectPoints.pop();
    }
    drawCanvas();
    updatePointCount();
    updateShapeType();
}

function updatePointCount() {
    // Zeige Anzahl der Kompositions-Punkte (für Form-Typ)
    document.getElementById('pointCount').textContent = compositionPoints.length;
}

function getExpectedShapeType(pointCount) {
    // Berechnet den erwarteten Form-Typ basierend auf Punktanzahl (Kompositions-Punkte)
    const mapping = SHAPE_TYPE_MAPPING[pointCount];
    if (mapping) {
        return mapping.value;
    } else if (pointCount > 10) {
        return 'polygon';
    } else {
        return 'custom';
    }
}

function updateShapeType() {
    const pointCount = compositionPoints.length; // Verwende Kompositions-Punkte
    const shapeTypeSelect = document.getElementById('shapeType');
    
    // Automatische Auswahl basierend auf Punktanzahl - nur wenn Auto-Modus aktiv
    if (isAutoMode) {
        const autoType = getExpectedShapeType(pointCount);
        
        // Aktualisiere den Wert immer, wenn Auto-Modus aktiv ist
        shapeTypeSelect.value = autoType;
    }
}

async function loadRandomImage() {
    console.log('loadRandomImage() aufgerufen');
    try {
        console.log('Starte Fetch zu /api/random-image');
        const response = await fetch('/api/random-image');
        console.log('Response erhalten:', response.status, response.statusText);
        
        if (!response.ok) {
            // Versuche JSON-Fehler zu lesen
            let errorMessage = 'Fehler beim Laden des zufälligen Bildes';
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
                console.error('Backend-Fehler:', errorData);
            } catch (e) {
                console.error('Fehler beim Lesen der Fehlerantwort:', e);
            }
            console.error('Fehler beim Laden:', errorMessage);
            // Beim automatischen Laden (beim Start) kein Alert zeigen, nur in Konsole loggen
            // Alert nur zeigen wenn Button manuell geklickt wurde
            // Prüfe ob es ein automatischer Aufruf ist (kein Event-Objekt vorhanden)
            const isAutoLoad = typeof event === 'undefined' || !event;
            if (!isAutoLoad) {
                alert(errorMessage);
            }
            return;
        }
        
        // Hash aus Header lesen
        const imageHash = response.headers.get('X-Image-Hash');
        console.log('Image Hash erhalten:', imageHash);
        
        console.log('Blob wird geladen...');
        const blob = await response.blob();
        console.log('Blob geladen, Größe:', blob.size);
        
        // Prüfe ob Blob leer ist
        if (blob.size === 0) {
            console.error('Blob ist leer');
            alert('Das geladene Bild ist leer. Bitte prüfen Sie die Bilddateien.');
            return;
        }
        
        // Verwende Hash-basierte URL statt Blob-URL
        const imageUrl = imageHash ? `/api/image/${imageHash}` : URL.createObjectURL(blob);
        console.log('Image URL erstellt:', imageUrl);
        
        const img = new Image();
        img.onload = async () => {
            console.log('Bild geladen, Dimensionen:', img.width, 'x', img.height);
            currentImage = img;
            imageLoaded = true;
            
            // Hash setzen (aus Header oder berechnen)
            if (imageHash) {
                currentImageHash = imageHash;
            } else {
                // Fallback: Hash berechnen
                currentImageHash = await getImageHash(img);
            }
            
            // Zurücksetzen der Punkte und Modi
            subjectPoints = [];
            compositionPoints = [];
            currentMode = 'subject';
            updateModeButton();
            
            // Canvas-Größe anpassen
            const maxWidth = window.innerWidth - 400; // Platz für Sidebar
            const maxHeight = window.innerHeight - 150; // Platz für Toolbar
            
            let width = img.width;
            let height = img.height;
            
            const scale = Math.min(maxWidth / width, maxHeight / height, 1);
            width *= scale;
            height *= scale;
            
            canvas.width = width;
            canvas.height = height;
            
            // Versuche vorhandene Annotationen zu laden
            await loadExistingAnnotation();
            
            drawCanvas();
            updatePointCount();
            updateShapeType();
            
            // Blob-URL nur freigeben wenn verwendet
            if (!imageHash && imageUrl.startsWith('blob:')) {
                URL.revokeObjectURL(imageUrl);
            }
        };
        img.onerror = (e) => {
            console.error('Fehler beim Laden des Bildes:', e);
            alert('Fehler beim Anzeigen des Bildes. Bitte prüfen Sie die Bilddatei.');
            if (!imageHash && imageUrl.startsWith('blob:')) {
                URL.revokeObjectURL(imageUrl);
            }
        };
        img.src = imageUrl;
    } catch (error) {
        console.error('Error:', error);
        // Beim automatischen Laden kein Alert zeigen
        const isAutoLoad = typeof event === 'undefined' || !event;
        if (!isAutoLoad) {
            alert(`Fehler beim Laden des zufälligen Bildes: ${error.message}`);
        }
    }
}

// Vorhandene Annotation für das aktuelle Bild laden
async function loadExistingAnnotation() {
    if (!currentImageHash) return;
    
    try {
        const response = await fetch(`/api/annotation/${currentImageHash}`);
        if (response.ok) {
            const annotation = await response.json();
            
            // Original-Bildgröße aus der Annotation (falls gespeichert)
            const originalWidth = annotation.originalWidth || currentImage.width;
            const originalHeight = annotation.originalHeight || currentImage.height;
            
            // Skalierungsfaktor berechnen
            const scaleX = canvas.width / originalWidth;
            const scaleY = canvas.height / originalHeight;
            
            // Subjekt-Punkte laden (für Rückwärtskompatibilität auch 'points' prüfen)
            if (annotation.subjectPoints && annotation.subjectPoints.length > 0) {
                subjectPoints = annotation.subjectPoints.map(p => ({
                    x: p.x * scaleX,
                    y: p.y * scaleY
                }));
            } else if (annotation.points && annotation.points.length > 0) {
                // Rückwärtskompatibilität: alte Annotationen ohne subjectPoints
                subjectPoints = annotation.points.map(p => ({
                    x: p.x * scaleX,
                    y: p.y * scaleY
                }));
            }
            
            // Kompositions-Punkte laden
            if (annotation.compositionPoints && annotation.compositionPoints.length > 0) {
                compositionPoints = annotation.compositionPoints.map(p => ({
                    x: p.x * scaleX,
                    y: p.y * scaleY
                }));
            }
            
            // Modus setzen: Wenn Subjekt-Punkte vorhanden, zu Komposition wechseln
            if (subjectPoints.length > 0) {
                currentMode = 'composition';
                updateModeButton();
            }
            
            // Labels laden
            if (annotation.labels && Array.isArray(annotation.labels)) {
                selectedLabels = new Set(annotation.labels);
                
                // Füge Labels hinzu, die nicht in der Standardliste sind
                annotation.labels.forEach(label => {
                    if (!labels.includes(label)) {
                        labels.push(label);
                    }
                });
                
                // Labels neu rendern, falls neue hinzugefügt wurden
                if (annotation.labels.some(label => !DEFAULT_LABELS.includes(label))) {
                    loadLabels();
                }
                
                // Checkboxes setzen
                annotation.labels.forEach(label => {
                    const checkbox = document.getElementById(`label-${label}`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
            }
            
            // Form-Typ laden
            if (annotation.shapeType) {
                document.getElementById('shapeType').value = annotation.shapeType;
            }
            
            updatePointCount();
            console.log('Vorhandene Annotation geladen');
        }
    } catch (error) {
        console.error('Fehler beim Laden der Annotation:', error);
        // Wenn keine Annotation gefunden wird, ist das in Ordnung
    }
}

function loadLabels() {
    const checklist = document.getElementById('labelsChecklist');
    if (!checklist) {
        console.error('labelsChecklist Element nicht gefunden!');
        return;
    }
    
    checklist.innerHTML = '';
    
    labels.forEach(label => {
        const item = document.createElement('div');
        item.className = 'checklist-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `label-${label}`;
        checkbox.value = label;
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                selectedLabels.add(label);
            } else {
                selectedLabels.delete(label);
            }
        });
        
        const labelElement = document.createElement('label');
        labelElement.htmlFor = `label-${label}`;
        labelElement.textContent = label;
        
        item.appendChild(checkbox);
        item.appendChild(labelElement);
        checklist.appendChild(item);
    });
    
    console.log('Labels geladen:', labels.length);
}

function addNewLabel() {
    const input = document.getElementById('newLabelInput');
    const label = input.value.trim();
    
    if (label && !labels.includes(label)) {
        labels.push(label);
        loadLabels();
        input.value = '';
    }
}

async function saveAnnotation() {
    if (!imageLoaded || (subjectPoints.length === 0 && compositionPoints.length === 0)) {
        alert('Bitte laden Sie ein Bild und markieren Sie das Subjekt oder zeichnen Sie eine Komposition.');
        return;
    }
    
    if (!currentImageHash) {
        alert('Fehler: Bild-Hash konnte nicht berechnet werden.');
        return;
    }
    
    // Punkte in Original-Bildgröße speichern (für korrektes Laden später)
    const originalWidth = currentImage.width;
    const originalHeight = currentImage.height;
    const scaleX = originalWidth / canvas.width;
    const scaleY = originalHeight / canvas.height;
    
    const originalSubjectPoints = subjectPoints.map(p => ({
        x: p.x * scaleX,
        y: p.y * scaleY
    }));
    
    const originalCompositionPoints = compositionPoints.map(p => ({
        x: p.x * scaleX,
        y: p.y * scaleY
    }));
    
    // Verwende Hash-basierte URL statt Blob-URL
    const imageUrl = currentImageHash ? `/api/image/${currentImageHash}` : currentImage.src;
    
    const annotation = {
        imageHash: currentImageHash,
        image: imageUrl, // Hash-basierte URL statt Blob-URL
        subjectPoints: originalSubjectPoints, // Subjekt-Punkte in Original-Größe
        compositionPoints: originalCompositionPoints, // Kompositions-Punkte in Original-Größe
        originalWidth: originalWidth,
        originalHeight: originalHeight,
        shapeType: document.getElementById('shapeType').value,
        labels: Array.from(selectedLabels),
        timestamp: new Date().toISOString()
    };
    
    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(annotation)
        });
        
        if (response.ok) {
            alert('Annotation gespeichert!');
        } else {
            alert('Fehler beim Speichern der Annotation.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Fehler beim Speichern der Annotation.');
    }
}

function loadNextImage() {
    document.getElementById('imageInput').value = '';
    subjectPoints = [];
    compositionPoints = [];
    currentMode = 'subject'; // Zurück zu Subjekt-Modus
    selectedLabels.clear();
    imageLoaded = false;
    currentImage = null;
    currentImageHash = null;
    isAutoMode = true; // Zurücksetzen auf Auto-Modus
    updateModeButton();
    
    // Checkboxes zurücksetzen
    document.querySelectorAll('#labelsChecklist input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
    
    updatePointCount();
    updateShapeType(); // Setzt automatisch auf 'thirds' zurück
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

