import os
from flask import Flask, request, render_template_string
import cv2
import numpy as np
import hashlib
import binascii
import base58

# Disable OpenCL to ensure deterministic behavior
cv2.ocl.setUseOpenCL(False)

# Compute SIFT features and count keypoints

def compute_sift_features(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Image not loaded properly")
    image = cv2.equalizeHist(image)
    sift = cv2.SIFT_create(contrastThreshold=0.04, edgeThreshold=10, nfeatures=200)
    keypoints, descriptors = sift.detectAndCompute(image, None)
    count = len(keypoints)
    if descriptors is None:
        return np.array([]), count
    feature_vector = descriptors.flatten()
    return feature_vector, count

# Generate a hash from the feature vector

def generate_feature_vector_hash(feature_vector):
    adjustment_counter = 0
    while True:
        adjusted = np.roll(feature_vector, adjustment_counter)
        h = hashlib.sha256(adjusted.tobytes()).hexdigest()[:19]
        if '0' not in h and 'I' not in h:
            return h
        adjustment_counter += 1

# Base58 encoding utilities

def b58ec(hex_str):
    data = bytearray.fromhex(hex_str)
    return base58.b58encode(data).decode('ascii')

def b58dc(enc, trim=0):
    return base58.b58decode(enc)[:-trim]

def hh256(s):
    return binascii.hexlify(hashlib.sha256(hashlib.sha256(s).digest()).digest())

def burn(template):
    decoded = b58dc(template, trim=4)
    decoded_hex = binascii.hexlify(decoded).decode('ascii')
    check = hh256(decoded)[:8].decode('ascii')
    return b58ec(decoded_hex + check)

# Validate that the generated address is a proper BTC address

def validate_btc_address(addr):
    try:
        data = base58.b58decode_check(addr)
        return data[0] == 0x00
    except Exception:
        return False

# Set up upload folder and Flask app
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load the minting script for copy functionality
with open('minting_script.txt') as f:
    MINTING_SCRIPT = f.read()

# HTML template with form and result sections
HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Verification Tool - The Bitcoin Mint</title>
  <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {
        margin: 40px;
        background-color: #fff;
        color: #161616;
        line-height: 1.4;
        font-family: 'EB Garamond', serif;
    }
    input[type=file] { margin-bottom: 20px; }
    .result { margin-top: 30px; }
    button {
        margin: 5px 10px 5px 0;
        padding: 10px 20px;
        font-size: 1rem;
        font-family: 'FuturaBold', 'EB Garamond', sans-serif;
        background-color: #000;
        color: #fff;
        border: none;
        cursor: pointer;
    }
    .link-button {
        text-decoration: none;
        color: #ccc;
        font-family: 'EB Garamond', serif;
        font-size: 1rem;
    }
  </style>
</head>
<body>
  <h1></h1>
  <form method="post" enctype="multipart/form-data">
    <label>Upload Natural Standard Image:</label><br>
    <input type="file" name="file" required><br>
    <button type="submit">Generate Address</button>
  </form>

  {% if address %}
  <div class="result">
    <h2>BTC Mint Address</h2>
    <p>{{ address }}</p>

    <button onclick="copyScript()">Copy Minting Script</button>
    <button onclick="window.open('https://colab.research.google.com/','_blank')" class="link-button">Google Colab</button>
    <a href="https://ordinals.com/content/efc063a1bc6812f94e278b5f9ea0283e111db3a7ebe2225ca927462a4ce11688i0" target="_blank" class="link-button">See On-chain Minting Script</a>

    <h3>Want to verify it independently?</h3>
    <p>Copy the code and paste it into a Google Colab Notebook. Upload the Natural Standard Image and edit the script to ensure the 'THE NATURAL STANDARD IMAGE PATH HERE' matches your uploaded file path. Run the script again.</p>

    <textarea id="script" style="display:none;">{{ minting_script }}</textarea>
  </div>
  <script>
    function copyScript() {
      const txt = document.getElementById('script').value;
      navigator.clipboard.writeText(txt);
      alert('Minting script copied to clipboard');
    }
  </script>
  {% endif %}
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    address = None
    kp_count = None
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(path)
            feature_vector, kp_count = compute_sift_features(path)
            hash_hex = generate_feature_vector_hash(feature_vector)
            template = f"1BtcMint{hash_hex}XXXXXXX"
            address = burn(template)
    return render_template_string(HTML_TEMPLATE, address=address, keypoints_count=kp_count, minting_script=MINTING_SCRIPT)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
