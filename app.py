import os
import logging
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import subprocess
from dotenv import load_dotenv

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

logging.info("Application started. Checking directories...")

# Log directories
if os.path.exists(UPLOAD_FOLDER):
    logging.info(f"Upload folder exists: {UPLOAD_FOLDER}")
else:
    logging.error(f"Upload folder missing: {UPLOAD_FOLDER}")

if os.path.exists(EXECUTABLE_FOLDER):
    logging.info(f"Executable folder exists: {EXECUTABLE_FOLDER}")
else:
    logging.error(f"Executable folder missing: {EXECUTABLE_FOLDER}")

# Email Configuration
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
PASSWORD = os.getenv('PASSWORD')
SUBJECT = os.getenv('SUBJECT', 'QUICK MAIL')  # Default subject if not in .env

def send_email(sender_email, password, receiver_email, subject, body):
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

        logging.info(f"Email sent to {receiver_email}")
        return "🎉 Email Sent Successfully"
    except Exception as e:
        logging.error(f"Error occurred while sending email: {str(e)}")
        return f"Error Occurred: {e}"

# Routes
@app.route('/')
def home():
    logging.info("Home route accessed.")
    return render_template('index.html')

@app.route('/installer', methods=['GET'])
def installer():
    logging.info("Installer route accessed.")
    return render_template('installer.html')

@app.route('/mail', methods=['GET'])
def mail():
    logging.info("Mail route accessed.")
    return render_template('mail.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            logging.warning("No file part in the request.")
            return 'No file part'
        
        file = request.files['file']
        if file.filename == '':
            logging.warning("No file selected for upload.")
            return 'No selected file'
        
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            logging.info(f"File uploaded: {file_path}")

            # Generate Executable
            executable_name = os.path.splitext(filename)[0] + ".exe"
            executable_path = os.path.join(app.config['EXECUTABLE_FOLDER'], executable_name)

            if os.path.exists(executable_path):
                os.remove(executable_path)
                logging.info(f"Old executable removed: {executable_path}")

            try:
                logging.debug("Running PyInstaller...")
                result = subprocess.run(
                    ['pyinstaller', '--onefile', '--distpath', app.config['EXECUTABLE_FOLDER'], file_path],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logging.debug(f"PyInstaller output: {result.stdout}")
                if os.path.exists(executable_path):
                    logging.info(f"Executable created: {executable_path}")
                    return redirect(url_for('download_file', filename=executable_name))
                else:
                    logging.error(f"Executable not created at: {executable_path}")
                    return f"Executable not created. Check logs for details.", 500

            except subprocess.CalledProcessError as e:
                logging.error(f"PyInstaller error: {e.stderr}")
                return f"Error creating executable: {e.stderr}", 500

    return render_template('installer.html')

@app.route('/download/<filename>')
def download_file(filename):
    executable_path = os.path.join(app.config['EXECUTABLE_FOLDER'], filename)
    if os.path.exists(executable_path):
        logging.info(f"File downloaded: {executable_path}")
        return send_from_directory(app.config['EXECUTABLE_FOLDER'], filename, as_attachment=True)
    else:
        logging.error(f"File not found for download: {executable_path}")
        return "File not found", 404

@app.route('/send-email', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        receiver_email = request.form.get('receiver_email')
        body = request.form.get('body')
        if not receiver_email or not body:
            logging.warning("Email form submitted with missing fields.")
            return "Receiver email and message body are required", 400
        
        result = send_email(SENDER_EMAIL, PASSWORD, receiver_email, SUBJECT, body)
        return render_template('mail.html', message=result)
    
    logging.info("Send email form accessed.")
    return render_template('mail.html')

# Main
if __name__ == '__main__':
    logging.info("Starting the Flask application...")
    app.run(host='0.0.0.0', port=3000)
