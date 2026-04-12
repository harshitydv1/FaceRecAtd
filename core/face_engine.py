"""
face_engine.py — Face recognition helpers
Uses the `face_recognition` library (dlib-based).
"""

import numpy as np
from PIL import Image, ImageDraw

TOLERANCE = 0.50  # lower = stricter match


def _to_rgb(pil_image: Image.Image) -> np.ndarray:
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    return np.array(pil_image)


def encode_face(pil_image: Image.Image):
    """
    Detect and encode a single face from a PIL Image.
    Returns (encoding | None, success: bool, message: str)
    """
    try:
        import face_recognition

        arr = _to_rgb(pil_image)
        locations = face_recognition.face_locations(arr, model="hog")

        if len(locations) == 0:
            return None, False, "❌ No face detected. Ensure good lighting and face is clearly visible."
        if len(locations) > 1:
            return None, False, f"❌ {len(locations)} faces detected. Please use a single-face photo."

        encodings = face_recognition.face_encodings(arr, locations)
        return encodings[0], True, "✅ Face encoded successfully."
    except ImportError:
        return None, False, "face_recognition library not installed. Run: pip install face-recognition"
    except Exception as e:
        return None, False, f"Error: {e}"


def identify_faces(pil_image: Image.Image, known_encodings: list):
    """
    Identify faces in an image against a list of known encodings.
    known_encodings: [{"user_id", "employee_id", "name", "encoding"}, ...]
    Returns: list of result dicts with keys: matched, user, confidence, location
    """
    if not known_encodings:
        return []

    try:
        import face_recognition

        arr = _to_rgb(pil_image)
        locations = face_recognition.face_locations(arr, model="hog")
        if not locations:
            return []

        face_encs = face_recognition.face_encodings(arr, locations)
        all_known = [e["encoding"] for e in known_encodings]

        results = []
        for enc, loc in zip(face_encs, locations):
            distances = face_recognition.face_distance(all_known, enc)
            best = int(np.argmin(distances))
            if distances[best] <= TOLERANCE:
                conf = round((1 - float(distances[best])) * 100, 1)
                results.append({
                    "matched": True,
                    "user": known_encodings[best],
                    "confidence": conf,
                    "location": loc,
                })
            else:
                results.append({
                    "matched": False,
                    "user": None,
                    "confidence": 0.0,
                    "location": loc,
                })
        return results
    except ImportError:
        return []
    except Exception:
        return []


def annotate_image(pil_image: Image.Image, results: list) -> Image.Image:
    """Draw labelled bounding boxes on detected faces."""
    img = pil_image.copy()
    draw = ImageDraw.Draw(img)

    for r in results:
        top, right, bottom, left = r["location"]
        color = "#00e676" if r["matched"] else "#ff1744"
        draw.rectangle([left, top, right, bottom], outline=color, width=3)
        label = f"{r['user']['name']} ({r['confidence']}%)" if r["matched"] else "Unknown"
        # background for label
        draw.rectangle([left, bottom - 22, right, bottom], fill=color)
        draw.text((left + 4, bottom - 19), label, fill="#000000")

    return img
