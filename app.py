import os
from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string

# Set up upload folder and Flask app
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# HTML template with only the upload form
HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Verification Tool - The Bitcoin Mint</title>
  <style>
    body { font-family: serif; margin: 40px; }
    input[type=file] { margin-bottom: 20px; }
    button { padding: 8px 16px; font-family: serif; }
  </style>
</head>
<body>
  <h1>The Bitcoin Mint Verification Tool</h1>
  <form action="/upload_for_colab" method="POST" enctype="multipart/form-data">
    <label for="natural_standard">Choose your Natural Standard image:</label><br>
    <input type="file" name="natural_standard" id="natural_standard" accept="image/*" required><br>
    <button type="submit">Verify in Google Colab</button>
  </form>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload_for_colab', methods=['POST'])
def upload_for_colab():
    file = request.files.get('natural_standard')
    if file:
        filename = file.filename
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        # Generate public URL for Colab
        file_url = request.url_root.rstrip('/') + url_for('uploaded_file', filename=filename)
        # Build Colab redirect URL pointing to hosted notebook with image parameter
        github_notebook = "https://colab.research.google.com/github/YourUser/bitcoin-mint-verify/blob/main/verify.ipynb"
        colab_link = f"{github_notebook}?url={file_url}"
        return redirect(colab_link)
    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
