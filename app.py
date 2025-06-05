import os
from flask import Flask, request, render_template_string, redirect, url_for, send_from_directory
import cv2
import numpy as np
import hashlib
import binascii
import base58

# Disable OpenCL to ensure deterministic behavior
cv2.ocl.setUseOpenCL(False)

# Compute SIFT features
def compute_sift_features(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("Image not loaded properly")
    image = cv2.equalizeHist(image)
    sift = cv2.SIFT_create(contrastThreshold=0.04, edgeThreshold=10, nfeatures=200)
    keypoints, descriptors = sift.detectAndCompute(image, None)
    if descriptors is None:
        return np.array([])
    return descriptors.flatten()

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

# Set up upload folder and Flask app
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load the minting script for “Copy Minting Script” button
with open('minting_script.txt') as f:
    MINTING_SCRIPT = f.read()

# HTML template with two forms:
#  - The first (GET) shows just the “Verify in Google Colab” button.
#  - Once an image is processed, we show the minted address + buttons.
HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Verification Tool – The Bitcoin Mint</title>
  <style>
    body { font-family: serif; margin: 40px; }
    input[type=file] { margin-bottom: 20px; }
    .result { margin-top: 30px; }
    button, .link-button { 
      margin: 5px 10px 5px 0; 
      padding: 8px 16px; 
      font-family: serif;
      text-decoration: none;
      background: #000;
      color: #fff;
      border: none;
      cursor: pointer;
    }
    .link-button { 
      background: transparent; 
      color: #999; 
      font-size: 1rem; 
      border: none; 
      padding: 0; 
      margin: 0 1rem 0 0;
    }
    .link-button:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>The Bitcoin Mint Verification Tool</h1>

  <form action="/upload_for_colab" method="POST" enctype="multipart/form-data">
    <label for="natural_standard">Choose your Natural Standard image:</label><br>
    <input type="file" name="natural_standard" id="natural_standard" accept="image/*" required><br>
    <button type="submit">Verify in Google Colab</button>
  </form>

  {% if address %}
  <div class="result">
    <h2>BTC Mint Address</h2>
    <p>{{ address }}</p>

    <!-- Copy the local minting_script.txt to clipboard -->
    <button onclick="copyScript()">Copy Minting Script</button>
    <!-- Open Colab with the file URL as a query parameter -->
    <a href="https://colab.research.google.com/?file={{ colab_url }}" target="_blank" class="link-button">Google Colab</a>
    <!-- Link to on-chain Ordinals script -->
    <a href="https://ordinals.com/content/efc063a1bc6812f94e278b5f9ea0283e111db3a7ebe2225ca927462a4ce11688i0" 
       target="_blank" class="link-button">See On-chain Minting Script</a>

    <h3>Want to verify it independently?</h3>
    <p>
      Copy the code and paste it into a Google Colab Notebook. Upload the Natural Standard Image 
      and edit the script so that <code>'THE NATURAL STANDARD IMAGE PATH HERE'</code> matches your uploaded file path. Run the script again.
    </p>
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

@app.route('/', methods=['GET'])
def index():
    # Simply show the form
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_for_colab', methods=['POST'])
def upload_for_colab():
    file = request.files.get('natural_standard')
    if not file:
        return redirect(url_for('index'))

    # Save the uploaded file to uploads/
    filename = file.filename
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    # Immediately compute the BTC address for display
    feature_vector = compute_sift_features(path)
    hash_hex = generate_feature_vector_hash(feature_vector)
    address = burn(f"1BtcMint{hash_hex}XXXXXXX")

    # Build a public URL to /uploads/<filename>
    file_url = request.url_root.rstrip('/') + url_for('uploaded_file', filename=filename)

    # Re-render the page, passing address + the Colab URL parameter
    return render_template_string(
        HTML_TEMPLATE,
        address=address,
        colab_url=file_url,
        minting_script=MINTING_SCRIPT
    )

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Serve the uploads/ directory so Colab can fetch it directly
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
