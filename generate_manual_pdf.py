"""
generate_manual_pdf.py
Genera MANUALE_VENUS_VORTEX.pdf a partire da MANUALE_VENUS_VORTEX.md.

Uso:
    python generate_manual_pdf.py
"""
import os
import sys
import markdown
from xhtml2pdf import pisa
from datetime import datetime


MD_FILE = "MANUALE_VENUS_VORTEX.md"
PDF_FILE = "MANUALE_VENUS_VORTEX.pdf"


# ==========================================
# CSS per il PDF
# ==========================================
CSS = """
@page {
    size: A4;
    margin: 2cm 1.8cm;
}

body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #1a1a1a;
}

h1 {
    color: #c026d3;
    font-size: 22pt;
    border-bottom: 2px solid #c026d3;
    padding-bottom: 6px;
    margin-top: 24px;
    margin-bottom: 12px;
}

h2 {
    color: #06b6d4;
    font-size: 16pt;
    margin-top: 22px;
    margin-bottom: 10px;
    border-bottom: 1px solid #e5e5e5;
    padding-bottom: 4px;
}

h3 {
    color: #a855f7;
    font-size: 13pt;
    margin-top: 16px;
    margin-bottom: 8px;
}

h4 {
    color: #333;
    font-size: 11pt;
    margin-top: 12px;
    margin-bottom: 6px;
}

p {
    margin-bottom: 8px;
    text-align: justify;
}

code {
    font-family: Courier, monospace;
    background: #f4f4f4;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9.5pt;
    color: #c026d3;
}

pre {
    background: #f4f4f4;
    padding: 10px;
    border-left: 3px solid #c026d3;
    font-size: 8.5pt;
    line-height: 1.35;
    font-family: Courier, monospace;
    margin: 8px 0;
    white-space: pre-wrap;
    word-wrap: break-word;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 6px 8px;
    text-align: left;
    font-size: 9.5pt;
}

th {
    background: #f9f9f9;
    font-weight: bold;
    color: #333;
}

blockquote {
    border-left: 4px solid #fbbf24;
    padding-left: 12px;
    color: #666;
    font-style: italic;
    margin: 10px 0;
}

ul, ol {
    margin-left: 20px;
    margin-bottom: 8px;
}

li {
    margin-bottom: 3px;
}

hr {
    border: none;
    border-top: 1px solid #e5e5e5;
    margin: 20px 0;
}

a {
    color: #06b6d4;
    text-decoration: none;
}

.cover {
    text-align: center;
    page-break-after: always;
    padding-top: 180px;
}

.cover h1 {
    font-size: 42pt;
    border: none;
    color: #c026d3;
    letter-spacing: 4px;
    margin-bottom: 20px;
}

.cover .subtitle {
    font-size: 16pt;
    color: #06b6d4;
    margin-bottom: 40px;
}

.cover .meta {
    margin-top: 100px;
    font-size: 11pt;
    color: #666;
}

.cover .meta p {
    margin-bottom: 6px;
}

.cover .vortex-symbol {
    font-size: 80pt;
    color: #a855f7;
    margin-bottom: 20px;
}
"""


# ==========================================
# Copertina
# ==========================================
def build_cover():
    data_oggi = datetime.now().strftime("%d/%m/%Y")
    return f"""
    <div class="cover">
        <div class="vortex-symbol">&#9737;</div>
        <h1>VENUS VORTEX</h1>
        <div class="subtitle">Manuale Tecnico v3.3.1</div>
        <div class="meta">
            <p><strong>Cosmic Pattern Engine</strong> per SuperEnalotto</p>
            <p>Autore: Francis490</p>
            <p>Generato il: {data_oggi}</p>
        </div>
    </div>
    """


# ==========================================
# Conversione Markdown -> PDF
# ==========================================
def md_to_pdf(md_path, pdf_path):
    if not os.path.exists(md_path):
        print(f"[!] File Markdown non trovato: {md_path}")
        sys.exit(1)

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    print(f"[*] Letto Markdown: {len(md_content)} caratteri")

    # Estensioni: tabelle, code block, indice, liste
    html_body = markdown.markdown(
        md_content,
        extensions=[
            "tables",
            "fenced_code",
            "toc",
            "sane_lists",
            "nl2br",
        ],
    )

    html_full = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Venus Vortex — Manuale Tecnico</title>
    <style>{CSS}</style>
</head>
<body>
    {build_cover()}
    {html_body}
</body>
</html>
"""

    print(f"[*] HTML generato: {len(html_full)} caratteri")

    # Converti in PDF
    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(html_full, dest=f, encoding="utf-8")

    if result.err:
        print(f"[!] Errore durante la generazione del PDF: {result.err}")
        sys.exit(1)

    size_kb = os.path.getsize(pdf_path) / 1024
    print(f"[+] PDF generato: {pdf_path} ({size_kb:.1f} KB)")


# ==========================================
# Main
# ==========================================
if __name__ == "__main__":
    print("=== GENERAZIONE MANUALE PDF ===")
    md_to_pdf(MD_FILE, PDF_FILE)
    print("=== COMPLETATO ===")
