import os

# --- Enforce single-threaded, disable OpenCL/accelerators BEFORE importing cv2 ---
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['OPENCV_OPENCL_RUNTIME'] = 'disabled'

import cv2
# Disable OpenCV internal threading & OpenCL
cv2.setNumThreads(0)
cv2.ocl.setUseOpenCL(False)

import numpy as np
import hashlib
import binascii
import base58
from flask import Flask, request, render_template_string, send_from_directory
from werkzeug.utils import secure_filename

# -- Debug versions for verification --
print("OpenCV version:", cv2.__version__)
print("NumPy version:", np.__version__)
print("base58 version:", base58.__version__)

# -- SIFT feature extraction exactly as in Colab (no sorting) --
def compute_sift_features(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Image not loaded properly")
    image = cv2.equalizeHist(image)

    sift = cv2.SIFT_create(
        contrastThreshold=0.04,
        edgeThreshold=10,
        nfeatures=200
    )
    keypoints, descriptors = sift.detectAndCompute(image, None)
    if descriptors is None:
        return np.array([]), image

    feature_vector = descriptors.flatten()
    vis = cv2.drawKeypoints(image, keypoints, None)
    return feature_vector, vis

# -- Hash & address generation --
def generate_feature_vector_hash(feature_vector):
    counter = 0
    while True:
        rolled = np.roll(feature_vector, counter)
        h = hashlib.sha256(rolled.tobytes()).hexdigest()[:19]
        if '0' not in h and 'I' not in h:
            return h
        counter += 1

def b58ec(hexstr):
    return base58.b58encode(bytearray.fromhex(hexstr)).decode('ascii')

def b58dc(encoded, trim=0):
    raw = base58.b58decode(encoded)
    return raw[:-trim]

def hh256(data):
    d1 = hashlib.sha256(data).digest()
    return binascii.hexlify(hashlib.sha256(d1).digest())

def burn(template_str):
    payload = b58dc(template_str, trim=4)
    hexed = binascii.hexlify(payload).decode('ascii')
    check = hh256(payload)[:8].decode('ascii')
    return b58ec(hexed + check)

def validate_btc_address(addr):
    try:
        raw = base58.b58decode_check(addr)
        return raw[0] == 0x00
    except Exception:
        return False

# -- HTML templates --
FORM = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Verify Natural Standard</title>
  <style>
    button { margin: 0.5rem 0.25rem; padding: 0.5rem 1rem; }
    pre { background: #f4f4f4; padding: 1rem; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>Upload Natural Standard Image</h1>
  <form method="post" enctype="multipart/form-data">
    <input type="file" name="image" accept="image/*" required>
    <button type="submit">Compute Address</button>
  </form>
</body>
</html>
"""

# Read minting script from external file for copy functionality
with open('minting_script.txt', 'r') as msf:
    MINT_SCRIPT = msf.read()

RESULT = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Verification Result</title>
  <style>
    button { margin: 0.5rem 0.25rem; padding: 0.5rem 1rem; }
    textarea { width:100%; height:200px; }
  </style>
</head>
<body>
  <h1>Verification Result</h1>
  <p><strong>BTC Address:</strong> {{ address }}<br><em>Valid format?</em> {{ 'yes' if valid else 'no' }}</p>
  {% if image_url %}
    <h2>Natural Standard SIFT Keypoints</h2>
    <img src="/uploads/{{ image_url }}" style="max-width:100%;height:auto;" alt="Keypoints">
  {% endif %}

  <hr>
  <h2>Want to verify it independently?</h2>
  <p>Copy the code and paste it into a Google Colab Notebook. Upload the Natural Standard Image and edit the script to ensure the 'NATURAL STANDARD IMAGE PATH HERE' matches your uploaded file path. Run the script again.</p>

  <button onclick="copyMintScript()">Copy Minting Script</button>
  <a href="https://ordinals.com/content/efc063a1bc6812f94e278b5f9ea0283e111db3a7ebe2225ca927462a4ce11688i0" target="_blank"><button>See On-chain Minting Script</button></a>
  <a href="https://colab.research.google.com/" target="_blank"><button>Google Colab</button></a>

  <textarea id="mintScript" readonly>{{ mint_script }}</textarea>

  <script>
    function copyMintScript() {
      const txt = document.getElementById('mintScript');
      txt.select();
      document.execCommand('copy');
      alert('Minting script copied!');
    }
  </script>
</body>
</html>
"""

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        f = request.files['image']
        filename = secure_filename(f.filename)
        in_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(in_path)

        fv, kp_img = compute_sift_features(in_path)
        feature_hash = generate_feature_vector_hash(fv)
        template = f"1BtcMint{feature_hash}XXXXXXX"
        address = burn(template)
        valid = validate_btc_address(address)

        kp_name = f"kp_{filename}"
        cv2.imwrite(os.path.join(app.config['UPLOAD_FOLDER'], kp_name), kp_img)

        return render_template_string(
            RESULT,
            address=address,
            valid=valid,
            image_url=kp_name,
            mint_script=MINT_SCRIPT
        )
    return render_template_string(FORM)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
