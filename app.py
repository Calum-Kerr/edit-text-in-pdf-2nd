import os, uuid, io, re
from flask import Flask, render_template, request, redirect, url_for, send_file, abort
import fitz  # PyMuPDF
from bs4 import BeautifulSoup  # new import for HTML processing
from weasyprint import HTML  # new import for HTML-to-PDF conversion
import base64  # new import

app = Flask(__name__)

# Global storage mapping pdf_id to a dict with original pdf bytes and extracted page texts
pdf_storage = {}

@app.route('/')
def index():
    # Redirect to upload page
    return redirect(url_for('upload'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('pdf')
        if file and file.filename.lower().endswith('.pdf'):
            pdf_bytes = file.read()
            pdf_stream = io.BytesIO(pdf_bytes)
            try:
                doc = fitz.open(stream=pdf_stream, filetype="pdf")
            except Exception as e:
                return "Error reading PDF", 400
            extracted_pages = []
            # Extract text per page (preserving basic formatting)
            for page in doc:
                extracted_pages.append(page.get_text("html"))
            pdf_id = str(uuid.uuid4())
            pdf_storage[pdf_id] = {
                'bytes': pdf_bytes,
                'pages': extracted_pages
            }
            return redirect(url_for('edit', pdf_id=pdf_id))
        else:
            return "Please upload a valid PDF file", 400
    return render_template('upload.html')

@app.route('/edit', methods=['GET'])
def edit():
    pdf_id = request.args.get('pdf_id')
    if not pdf_id or pdf_id not in pdf_storage:
        abort(404)
    pages = pdf_storage[pdf_id]['pages']
    return render_template('edit.html', pdf_id=pdf_id, pages=pages)

@app.route('/download', methods=['POST'])
def download():
    pdf_id = request.form["pdf_id"]
    if pdf_id not in pdf_storage:
        abort(404)
    pdf_bytes = pdf_storage[pdf_id]['bytes']
    stream = io.BytesIO(pdf_bytes)
    doc = fitz.open(stream=stream, filetype="pdf")
    
    for i, page in enumerate(doc):
        new_page_text = request.form.get(f'page_{i}', '').strip()
        orig_str = "Calum Kerr"
        new_str = new_page_text.replace("Calum Kerr", "Calam")
        
        areas = page.search_for(orig_str)
        if not areas:
            print(f"No occurrences found on page {i}. Inserting fallback text for testing.")
            # Fallback: insert text at a fixed position to verify insertion works.
            page.insert_text(
                (50, 50),
                new_str,
                fontname="Times-Roman",
                fontsize=11.5,
                color=(0, 0, 0)
            )
        else:
            for rect in areas:
                new_rect = fitz.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                page.insert_textbox(
                    new_rect,
                    new_str,
                    fontname="Times-Roman",
                    fontsize=11.5,
                    align=fitz.TEXT_ALIGN_LEFT,
                    color=(0, 0, 0)
                )
    output_stream = io.BytesIO()
    doc.save(output_stream)
    output_stream.seek(0)
    return send_file(
        output_stream, 
        mimetype='application/pdf', 
        as_attachment=True, 
        download_name=f"{pdf_id}_edited.pdf"
    )

if __name__ == '__main__':
    app.run(debug=True)
