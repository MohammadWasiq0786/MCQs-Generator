import os
from flask import Flask, render_template, request, send_file
import pdfplumber
import docx
from werkzeug.utils import secure_filename
from fpdf import FPDF
from db import init_db, save_to_db
from euriai import EuriaiClient
from dotenv import load_dotenv

# Load model
EURI_API_KEY = os.getenv("EURI_API_KEY")
client = EuriaiClient(api_key=EURI_API_KEY, model="gpt-4.1-nano")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['RESULTS_FOLDER'] = 'results/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'txt', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_file(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        with pdfplumber.open(file_path) as pdf:
            return ''.join([page.extract_text() or '' for page in pdf.pages])
    elif ext == 'docx':
        doc = docx.Document(file_path)
        return ' '.join([para.text for para in doc.paragraphs])
    elif ext == 'txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    return None

def generate_mcqs(input_text, num_questions):
    prompt = f"""
You are an AI assistant helping to generate multiple-choice questions (MCQs) from the following content:

\"\"\"{input_text}\"\"\"

Generate {num_questions} MCQs. Each should include:
- A question
- Options A, B, C, D
- Correct answer

Format:
## MCQ
Question: ...
A) ...
B) ...
C) ...
D) ...
Correct Answer: ...
    """

    response = client.generate_completion(prompt=prompt, temperature=0.5, max_tokens=1000)
    ai_text = response['choices'][0]['message']['content'] if 'choices' in response else ""
    
    # response = model.generate_content(prompt)
    # return response.text.strip() 
    return ai_text.strip()

def save_mcqs_to_file(mcqs, filename):
    path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(mcqs)
    return path

import unicodedata

def clean_text(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

def create_pdf(mcqs, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for mcq in mcqs.split("## MCQ"):
        if mcq.strip():
            clean_mcq = clean_text(mcq.strip())
            pdf.multi_cell(0, 10, clean_mcq)
            pdf.ln(5)

    pdf_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    pdf.output(pdf_path)
    return pdf_path


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    if 'file' not in request.files:
        return "No file part"

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        text = extract_text_from_file(filepath)
        if not text:
            return "Could not extract text from the file."

        num_questions = int(request.form['num_questions'])
        mcqs = generate_mcqs(text, num_questions)

        # Save to SQLite
        save_to_db(filename, num_questions, text, mcqs)

        # Save to files
        txt_file = f"generated_mcqs_{filename.rsplit('.', 1)[0]}.txt"
        pdf_file = f"generated_mcqs_{filename.rsplit('.', 1)[0]}.pdf"
        save_mcqs_to_file(mcqs, txt_file)
        create_pdf(mcqs, pdf_file)

        return render_template('results.html',
                               mcqs=mcqs,
                               txt_filename=txt_file,
                               pdf_filename=pdf_file)

    return "Invalid file format"

@app.route('/download/<filename>')
def download_file(filename):
    path = os.path.join(app.config['RESULTS_FOLDER'], filename)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
    os.makedirs('database', exist_ok=True)
    init_db()
    app.run(debug=True)
