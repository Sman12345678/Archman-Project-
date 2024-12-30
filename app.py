import os
import logging
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import subprocess
from dotenv import load_dotenv  # Import dotenv

# Load environment variables
load_dotenv()

# Flask App Configuration
UPLOAD_FOLDER = 'uploads'
EXECUTABLE_FOLDER = 'executables'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EXECUTABLE_FOLDER'] = EXECUTABLE_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limit file size to 10MB

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXECUTABLE_FOLDER, exist_ok=True)

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logging.info("Application started and directories are being checked...")

# Log directories
if os.path.exists(UPLOAD_FOLDER):
    logging.info(f"Upload folder exists: {UPLOAD_FOLDER}")
else:
    logging.error(f"Upload folder missing: {UPLOAD_FOLDER}")

if os.path.exists(EXECUTABLE_FOLDER):
    logging.info(f"Executable folder exists: {EXECUTABLE_FOLDER}")
else:
    logging.error(f"Executable folder missing: {EXECUTABLE_FOLDER}")

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if file part exists
        if 'file' not in request.files:
            logging.warning("No file part in the request.")
            return 'No file part'
        
        file = request.files['file']
        if file.filename == '':
            logging.warning("No file selected for upload.")
            return 'No selected file'
        
        if file:
            # Save file securely
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            logging.info(f"File uploaded and saved to {file_path}")

            # Generate Executable
            executable_name = os.path.splitext(filename)[0] + ".exe"
            executable_path = os.path.join(app.config['EXECUTABLE_FOLDER'], executable_name)

            # Remove existing executable (if any) to avoid conflicts
            if os.path.exists(executable_path):
                os.remove(executable_path)
                logging.info(f"Old executable removed: {executable_path}")

            try:
                logging.debug("Running PyInstaller to generate executable...")
                result = subprocess.run(
                    ['pyinstaller', '--onefile', '--distpath', app.config['EXECUTABLE_FOLDER'], file_path],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logging.debug(f"PyInstaller output: {result.stdout}")
                logging.error(f"PyInstaller error (if any): {result.stderr}")

                # Check if the executable was created
                if os.path.exists(executable_path):
                    logging.info(f"Executable created successfully: {executable_path}")
                    return redirect(url_for('download_file', filename=executable_name))
                else:
                    logging.error(f"Executable not found at {executable_path}")
                    return f"Executable not created. Check logs for details.", 500

            except subprocess.CalledProcessError as e:
                logging.error(f"Error creating executable: {str(e)}")
                return f"Error creating executable: {str(e)}", 500

    return render_template('installer.html')

@app.route('/download/<filename>')
def download_file(filename):
    executable_path = os.path.join(app.config['EXECUTABLE_FOLDER'], filename)
    if os.path.exists(executable_path):
        logging.info(f"File being downloaded: {executable_path}")
        return send_from_directory(app.config['EXECUTABLE_FOLDER'], filename, as_attachment=True)
    else:
        logging.error(f"Requested file not found: {executable_path}")
        return "File not found", 404

# Main
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
