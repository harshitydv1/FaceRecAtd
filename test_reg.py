import io
import sys, os
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from core.face_engine import encode_face

# create dummy image bytes
img = Image.new('RGB', (100, 100), color = 'red')
buf = io.BytesIO()
img.save(buf, format='JPEG')
face_bytes = buf.getvalue()

face_img = Image.open(io.BytesIO(face_bytes))
encoding, ok, msg = encode_face(face_img)
print("encode result:", ok, msg)
