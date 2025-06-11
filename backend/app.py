from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import subprocess
import pandas as pd
import glob
import json
import time
import sys
import psutil
import logging
import threading
import shutil

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Enable debug mode
app.debug = True

# Configure Flask logging
app.logger.setLevel(logging.DEBUG)

# Disable werkzeug logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

UPLOAD_FOLDER = 'invoice_temp_storage'
STATEMENT_FOLDER = '.'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'csv'}

# Global variable to store progress
current_progress = {"processed": 0, "total": 0}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def log_request_info():
    logger.debug('Headers: %s', request.headers)
    logger.debug('Body: %s', request.get_data())

@app.route('/progress', methods=['GET'])
def get_progress():
    def generate():
        while True:
            # Send the current progress
            yield f"data: {json.dumps(current_progress)}\n\n"
            # If processing is complete, send a final message and break
            if current_progress["processed"] >= current_progress["total"] and current_progress["total"] > 0:
                yield f"data: {json.dumps({'complete': True})}\n\n"
                break
            time.sleep(0.5)  # Update every 0.5 seconds

    return Response(generate(), mimetype='text/event-stream')

@app.route('/uploaded-invoices', methods=['GET'])
def get_uploaded_invoices():
    try:
        # Get all files in the invoice storage folder
        files = []
        for ext in ALLOWED_EXTENSIONS:
            files.extend(glob.glob(os.path.join(UPLOAD_FOLDER, f'*.{ext}')))
        
        # Get file info
        file_info = []
        for file_path in files:
            file_info.append({
                'name': os.path.basename(file_path),
                'size': os.path.getsize(file_path),
                'uploaded_at': os.path.getctime(file_path)
            })
        
        return jsonify(file_info)
    except Exception as e:
        return jsonify({'error': f'Failed to get uploaded invoices: {str(e)}'}), 500

@app.route('/uploaded-statement', methods=['GET'])
def get_uploaded_statement():
    try:
        statement_path = os.path.join(STATEMENT_FOLDER, 'supplier_statement.csv')
        if os.path.exists(statement_path):
            return jsonify({
                'name': 'supplier_statement.csv',
                'size': os.path.getsize(statement_path),
                'uploaded_at': os.path.getctime(statement_path)
            })
        return jsonify(None)
    except Exception as e:
        return jsonify({'error': f'Failed to get uploaded statement: {str(e)}'}), 500

@app.route('/upload-invoices', methods=['POST'])
def upload_invoices():
    print("Received upload request")
    sys.stdout.flush()
    
    # Check for both possible field names
    if 'files[]' in request.files:
        files = request.files.getlist('files[]')
    elif 'invoices' in request.files:
        files = request.files.getlist('invoices')
    else:
        print("No files[] or invoices in request")
        sys.stdout.flush()
        return jsonify({'error': 'No file part'}), 400
    
    if not files or files[0].filename == '':
        print("No selected file")
        sys.stdout.flush()
        return jsonify({'error': 'No selected file'}), 400

    print(f"Received {len(files)} files")
    sys.stdout.flush()
    
    try:
        # Ensure the upload directory exists
        upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Check if we're in append mode
        append_mode = request.args.get('append', 'false').lower() == 'true'
        print(f"Append mode: {append_mode}")
        sys.stdout.flush()
        
        # If not in append mode, clear the directory first
        if not append_mode:
            print("Clearing upload directory...")
            sys.stdout.flush()
            for file in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
                    sys.stdout.flush()
        
        # Save new files
        saved_files = []
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                saved_files.append(filename)
                print(f"Saved file: {filepath}")
                sys.stdout.flush()
        
        if not saved_files:
            print("No files were saved")
            sys.stdout.flush()
            return jsonify({
                'success': True,
                'message': 'No files were saved',
                'files': []
            })

        # Process all files in the folder
        print("Starting invoice extraction on all files...")
        sys.stdout.flush()
        
        # Run extract_invoices.py on the entire folder
        extract_result = subprocess.run(['python', 'extract_invoices.py'], check=True)
        if extract_result.returncode != 0:
            raise Exception("Invoice extraction failed")
            
        print("Starting reconciliation...")
        sys.stdout.flush()
        
        # Run reconcile_data.py
        reconcile_result = subprocess.run(['python', 'reconcile_data.py'], check=True)
        if reconcile_result.returncode != 0:
            raise Exception("Reconciliation failed")
        
        return jsonify({
            'success': True,
            'message': 'Files uploaded and processed successfully',
            'files': saved_files
        })
        
    except Exception as e:
        print(f"Error during processing: {e}")
        sys.stdout.flush()
        return jsonify({'error': str(e)}), 500

@app.route('/upload-statement', methods=['POST'])
def upload_statement():
    if 'statement' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['statement']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(STATEMENT_FOLDER, 'supplier_statement.csv'))
        
        # Run the reconciliation script
        try:
            subprocess.run(['python', 'reconcile_data.py'], check=True)
            return jsonify({'success': True})
        except subprocess.CalledProcessError as e:
            return jsonify({'error': f'Failed to process statement: {str(e)}'}), 500

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/reconciliation-results', methods=['GET'])
def get_reconciliation_results():
    try:
        # Find the most recent reconciliation results file
        results_files = [f for f in os.listdir('reconcilliation_results') if f.startswith('reconciliation_results')]
        if not results_files:
            return jsonify({'error': 'No reconciliation results found'}), 404
        
        latest_file = max(results_files, key=lambda x: os.path.getctime(os.path.join('reconcilliation_results', x)))
        
        # Read the CSV file
        df = pd.read_csv(os.path.join('reconcilliation_results', latest_file))
        
        # Convert DataFrame to list of dictionaries
        results = df.to_dict('records')
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch results: {str(e)}'}), 500

@app.route('/export-reconciliation', methods=['GET'])
def export_reconciliation():
    try:
        # Find the most recent reconciliation results file
        results_files = [f for f in os.listdir('reconcilliation_results') if f.startswith('reconciliation_results')]
        if not results_files:
            return jsonify({'error': 'No reconciliation results found'}), 404
        
        latest_file = max(results_files, key=lambda x: os.path.getctime(os.path.join('reconcilliation_results', x)))
        file_path = os.path.join('reconcilliation_results', latest_file)
        
        # Send the file
        return send_file(
            file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=latest_file
        )
    except Exception as e:
        return jsonify({'error': f'Failed to export results: {str(e)}'}), 500

@app.route('/uploaded-invoices/<filename>', methods=['DELETE'])
def delete_uploaded_invoice(filename):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500

@app.route('/statement-preview', methods=['GET'])
def get_statement_preview():
    try:
        statement_path = os.path.join(STATEMENT_FOLDER, 'supplier_statement.csv')
        if not os.path.exists(statement_path):
            return jsonify({'error': 'No statement file found'}), 404
        
        # Read the entire CSV file
        df = pd.read_csv(statement_path)
        
        # Filter out unnamed columns (those starting with 'Unnamed:')
        named_columns = [col for col in df.columns if not str(col).startswith('Unnamed:')]
        df = df[named_columns]
        
        # Convert DataFrame to list of dictionaries
        preview_data = {
            'headers': df.columns.tolist(),
            'rows': df.fillna('').values.tolist()  # Replace NaN with empty string
        }
        
        print(f"Preview data: {len(preview_data['rows'])} rows")  # Debug print
        return jsonify(preview_data)
    except Exception as e:
        print(f"Error in statement preview: {str(e)}")  # Debug print
        return jsonify({'error': f'Failed to read statement preview: {str(e)}'}), 500

if __name__ == '__main__':
    # Create necessary directories if they don't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs('reconcilliation_results', exist_ok=True)
    
    logger.info("Starting Flask application...")
    app.run(debug=True, port=5000) 