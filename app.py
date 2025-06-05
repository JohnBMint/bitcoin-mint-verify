import os
from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string

# We keep cv2 imported only so that Flask starts correctly, but we never call compute_sift_features here.
import cv2  

# (You could remove all of your hashing/SIFT functions from this file if you’d like;
#  they will live inside your Colab notebook instead.)

# Create (if necessary) an uploads/ folder in the current working directory
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load the minting script text for “Copy Minting Script” functionality
with open('minting_script.txt', 'r') as f:
    MINTING_SCRIPT = f.read()

# A minimal HTML template.  On GET, it only shows the upload form.
# On POST (after upload), we inject “colab_url” so that the template shows the Google Colab button.
HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Verification Tool – The Bitcoin Mint</title>
  <style>
    body { 
      font-family: serif; 
      margin: 40px; 
    }
    input[type=file] { margin-bottom: 20px; }
    .result { margin-top: 30px; }
    button { 
      margin: 5px 10px 5px 0; 
      padding: 8px 16px; 
      font-family: serif; 
    }
    .link-button { 
      text-decoration: none; 
      color: #999; 
      font-family: serif; 
      font-size: 1rem; 
      margin-right: 10px;
    }
  </style>
</head>
<body>
  <h1>The Bitcoin Mint Verification Tool</h1>
  <form action="/upload_for_colab" method="POST" enctype="multipart/form-data">
    <label for="natural_standard">Choose your Natural Standard image:</label><br>
    <input type="file" name="natural_standard" id="natural_standard" accept="image/*" required><br>
    <button type="submit">Verify in Google Colab</button>
  </form>

  {% if colab_url %}
    <div class="result">
      <h2>Your file has been uploaded!</h2>
      <p>You can now launch the Colab notebook to run the minting script against your image.</p>
      <button onclick="copyScript()">Copy Minting Script</button>
      <a href="https://colab.research.google.com/notebook#create=true&url={{ colab_url }}" 
         target="_blank" class="link-button">Google Colab</a>
      <a href="https://ordinals.com/content/efc063a1bc6812f94e278b5f9ea0283e111db3a7ebe2225ca927462a4ce11688i0" 
         target="_blank" class="link-button">See On-chain Minting Script</a>

      <h3>Want to verify it independently?</h3>
      <p>
        Copy the code below, open a fresh Colab notebook, upload your Natural Standard image there, 
        set the path accordingly, and run the script to reproduce the BTC‐mint address yourself.
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
    # Just render the upload form (no colab_url yet)
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_for_colab', methods=['POST'])
def upload_for_colab():
    # 1) Save the uploaded file into /uploads
    file = request.files.get('natural_standard')
    if file:
        filename = file.filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        # 2) Build a publicly‐accessible URL for this file,
        #    which the Colab notebook can fetch.
        #
        #    We assume that the Flask route /uploads/<filename> will serve it.
        file_url = request.url_root[:-1] + url_for('uploaded_file', filename=filename)

        # 3) Render the same template, but now include colab_url so the
        #    “Google Colab” button appears.  The Colab link itself
        #    will pass our file_url as a URL‐parameter.
        return render_template_string(
            HTML_TEMPLATE,
            colab_url=file_url,
            minting_script=MINTING_SCRIPT
        )

    # If no file was actually uploaded, just redirect back to GET form
    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Serve the static file so Colab (and the user’s browser) can retrieve it.
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # In production, Flask’s debug/reloader must remain off.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
