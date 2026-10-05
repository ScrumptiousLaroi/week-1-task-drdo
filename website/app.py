from flask import Flask, flash, redirect, render_template, request, session, jsonify, send_from_directory
from flask_session import Session
import os
import subprocess
from datetime import datetime
import json
import papermill as pm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREDICTIONS_FOLDER = os.path.join(BASE_DIR, 'prediction')

# Configure application
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(BASE_DIR, 'flask_session')
Session(app)

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'csvFile' not in request.files:
        return "No file part"

    file = request.files['csvFile']

    if file.filename == '':
        return "No selected file"

    if file:
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        session['file_path'] = file_path  # Save the file path in the session
        try:
            session['seed'] = int(request.form.get('seed', 1))
        except ValueError:
            session['seed'] = 1
        return redirect('/process')

@app.route('/process', methods=['GET'])
def process():
    # Retrieve the file path from the session
    file_path = session.get('file_path')
    if not file_path:
        return "No file uploaded in this session"

    # Each run writes its own timestamped prediction file into the prediction folder
    os.makedirs(PREDICTIONS_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'output'), exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    prediction_path = os.path.join(PREDICTIONS_FOLDER, f'prediction_ic50_{stamp}.csv')
    metrics_path = os.path.join(BASE_DIR, 'output', f'metrics_{stamp}.json')

    result = run_notebook(file_path, session.get('seed', 1), prediction_path, metrics_path)
    if not os.path.exists(prediction_path):
        return f"Prediction failed: {result}", 500

    metrics = {}
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            metrics = json.load(f)

    return render_template('result.html', prediction_file_path=os.path.basename(prediction_path), metrics=metrics)

def run_notebook(file_path, seed=1, output_path=None, metrics_path=None):
    try:
        # Paths to the input and output notebooks
        input_notebook = os.path.join(BASE_DIR, 'Machine.ipynb')
        output_notebook = os.path.join(BASE_DIR, 'output', 'output_notebook.ipynb')

        # Run the notebook with papermill
        pm.execute_notebook(
            input_path=input_notebook,
            output_path=output_notebook,
            parameters=dict(file_path=file_path, seed=seed, output_path=output_path, metrics_path=metrics_path),
            cwd=BASE_DIR
        )

        return "Notebook executed successfully"
    except Exception as e:
        return str(e)

@app.route('/api/predictions', methods=['GET']) # Used github copilot
def list_predictions():
    files = []
    for filename in os.listdir(PREDICTIONS_FOLDER):
        filepath = os.path.join(PREDICTIONS_FOLDER, filename)
        if os.path.isfile(filepath):
            creation_time = os.path.getctime(filepath)
            files.append({
                'name': filename,
                'creationTime': datetime.fromtimestamp(creation_time).isoformat()
            })
    return jsonify(files)

@app.route('/predictions/<filename>', methods=['GET']) # used github co pilot to save the predicted file in the prediction folder
def download_prediction(filename):
    return send_from_directory(PREDICTIONS_FOLDER, filename)



if __name__ == '__main__':
    app.run(debug=True)

if __name__ == '__main__':
    app.run(debug=True)
