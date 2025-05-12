from flask import Flask, render_template, request, jsonify
import os
import re
import PyPDF2
import docx
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_text_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    text = " ".join(df.astype(str).values.flatten())
    return text

def extract_text_from_excel(excel_path):
    df = pd.read_excel(excel_path)
    text = " ".join(df.astype(str).values.flatten())
    return text

def extract_text(file_path):
    file_extension = file_path.rsplit('.', 1)[1].lower()
    
    if file_extension == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_extension == 'docx':
        return extract_text_from_docx(file_path)
    elif file_extension == 'txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    elif file_extension == 'csv':
        return extract_text_from_csv(file_path)
    elif file_extension == 'xlsx':
        return extract_text_from_excel(file_path)
    return ""

def check_keywords(text, keywords):
    """Check if keywords exist in the text and return results with context."""
    text = text.lower()
    results = []
    
    for keyword in keywords:
        keyword = keyword.lower()
        present = keyword in text
        context = ""
        
        if present:
            # Find the keyword in context
            match = re.search(f'.{{0,40}}{re.escape(keyword)}.{{0,40}}', text)
            if match:
                context = f"...{match.group(0)}..."
        
        results.append({
            'keyword': keyword,
            'present': present,
            'context': context
        })
    
    # Calculate statistics
    total = len(results)
    present_count = sum(1 for r in results if r['present'])
    missing_count = total - present_count
    match_score = round((present_count / total) * 100) if total > 0 else 0
    
    return {
        'keywords': results,
        'stats': {
            'total': total,
            'present': present_count,
            'missing': missing_count,
            'score': match_score
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check_resume():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    keywords_text = request.form.get('keywords', '')
    if not keywords_text.strip():
        return jsonify({'error': 'No keywords provided'})
    
    # Process keywords - split by commas, newlines, or spaces
    keywords = re.split(r'[,\n\s]+', keywords_text)
    keywords = [k.strip() for k in keywords if k.strip()]
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Extract text from the file
            text = extract_text(file_path)
            
            # Check for keywords
            results = check_keywords(text, keywords)
            
            # Clean up the uploaded file
            os.remove(file_path)
            
            return jsonify(results)
        except Exception as e:
            # Clean up on error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': str(e)})
    
    return jsonify({'error': 'Invalid file type'})

if __name__ == '__main__':
    app.run(debug=True)