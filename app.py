import os
import logging
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Flask App Configuration
UPLOAD_FOLDER = 'uploads'
EXECUTABLE_FOLDER = 'executables'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EXECUTABLE_FOLDER'] = EXECUTABLE_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limit file size to 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXECUTABLE_FOLDER, exist_ok=True)

# Email Credentials from .env
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
PASSWORD = os.getenv('PASSWORD')
SUBJECT = os.getenv('SUBJECT', 'QUICK MAIL')  # Default subject if not in .env

# Handle Email Sending
def send_email(sender_email, password, receiver_email, subject, body):
    try:
        logging.debug("Preparing email...")
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject

        # Add Message Body
        msg.attach(MIMEText(body, "plain"))

        # Email Server Connection
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Encrypt Connection
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()  # Close Connection
        logging.info("Email sent successfully!")
        return "🎉 Email Sent Successfully"
    except Exception as e:
        logging.error(f"Error occurred while sending email: {e}")
        return f"Error Occurred: {e}"

# Routes

@app.route('/')
def home():
    logging.debug("Rendering home page...")
    return render_template('index.html')

@app.route('/installer', methods=['GET'])
def installer():
    logging.debug("Rendering installer page...")
    return render_template('installer.html')

@app.route('/mail', methods=['GET'])
def mail():
    logging.debug("Rendering mail page...")
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
            logging.info(f"File saved to {file_path}")

            # Generate Executable
            executable_name = os.path.splitext(filename)[0] + ".exe"
            executable_path = os.path.join(app.config['EXECUTABLE_FOLDER'], executable_name)
            try:
                logging.debug("Running pyinstaller...")
                subprocess.run(
                    ['pyinstaller', '--onefile', '--distpath', app.config['EXECUTABLE_FOLDER'], file_path],
                    check=True
                )
                logging.info(f"Executable created at {executable_path}")
                return redirect(url_for('download_file', filename=executable_name))
            except subprocess.CalledProcessError as e:
                logging.error(f"Error creating executable: {str(e)}")
                return f"Error creating executable: {str(e)}"
    return render_template('installer.html')

@app.route('/download/<filename>')
def download_file(filename):
    executable_path = os.path.join(app.config['EXECUTABLE_FOLDER'], filename)
    if not os.path.exists(executable_path):
        logging.error(f"File {filename} not found in {app.config['EXECUTABLE_FOLDER']}")
        return f"File {filename} not found.", 404
    logging.info(f"Serving file {filename} for download.")
    return send_from_directory(app.config['EXECUTABLE_FOLDER'], filename, as_attachment=True)

@app.route('/send-email', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        receiver_email = request.form['receiver_email']
        body = request.form['body']
        logging.debug(f"Sending email to {receiver_email}")
        result = send_email(SENDER_EMAIL, PASSWORD, receiver_email, SUBJECT, body)
        return render_template('mail.html', message=result)
    logging.debug("Rendering mail page...")
    return render_template('mail.html')

# Main
if __name__ == '__main__':
    logging.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=3000)
