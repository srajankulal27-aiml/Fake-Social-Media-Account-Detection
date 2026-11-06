"""Generate DOCUMENTATION.docx containing the complete project documentation.
"""
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def create_document():
    doc = Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Styles
    navy = RGBColor(20, 20, 58)       # #14143a
    purple = RGBColor(91, 45, 240)    # #5b2df0
    muted = RGBColor(91, 96, 121)     # #5b6079
    dark = RGBColor(15, 16, 51)       # #0f1033

    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("Fake Social Media Account Detection (FSMD)")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(24)
    run_title.font.bold = True
    run_title.font.color.rgb = navy

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("Comprehensive Technical Documentation & Architecture Specification")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(13)
    run_sub.font.color.rgb = purple

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Section 1
    h1 = doc.add_heading("1. Executive Summary & Problem Overview", level=1)
    h1.runs[0].font.color.rgb = navy
    
    doc.add_paragraph(
        "Social media platforms are saturated with automated bots, impersonators, and fraudulent accounts "
        "designed to manipulate engagement, disseminate spam, and execute credential harvesting. Modern moderation "
        "pipelines require reliable, explainable, and privacy-respecting triage mechanisms."
    )
    doc.add_paragraph(
        "FSMD (Fake Social Media Detection) is an end-to-end Machine Learning web platform and REST API built with "
        "Python 3.12 and FastAPI. It classifies social media profiles as Genuine or Fake/Bot using tabular profile metadata, "
        "activity metrics, and behavioral network ratios."
    )

    doc.add_heading("Core Design Principles", level=2)
    bp1 = doc.add_paragraph(style='List Bullet')
    r = bp1.add_run("No Scraping or Platform Access: ")
    r.bold = True
    bp1.add_run("Operates strictly on user-supplied inputs or profile screenshots. Never contacts Instagram or any live API.")

    bp2 = doc.add_paragraph(style='List Bullet')
    r = bp2.add_run("In-Memory Image Processing: ")
    r.bold = True
    bp2.add_run("Screenshots are analyzed in RAM (io.BytesIO) and are never saved to disk, logged, or stored in a database.")

    bp3 = doc.add_paragraph(style='List Bullet')
    r = bp3.add_run("No Facial Recognition: ")
    r.bold = True
    bp3.add_run("Inspects metadata and count fields only; never performs pixel-level facial recognition or personal biometric analysis.")

    bp4 = doc.add_paragraph(style='List Bullet')
    r = bp4.add_run("Local SHAP Explanations: ")
    r.bold = True
    bp4.add_run("Employs TreeSHAP on the production Random Forest model to produce per-prediction signed directional attributions (Toward Fake vs. Toward Genuine).")

    # Section 2
    h2 = doc.add_heading("2. System Architecture", level=1)
    h2.runs[0].font.color.rgb = navy

    doc.add_paragraph(
        "The application is structured into four decoupled layers:\n"
        "1. Client Layer: Server-rendered Jinja2 templates styled with Bootstrap 5 CDN and custom Plus Jakarta Sans design system. Vanilla JavaScript client logic provides interactive AJAX validation, real-time feature derivation, and Chart.js doughnut analytics.\n"
        "2. FastAPI Application Engine (app_api/): High-performance ASGI web server managing endpoints, schema validation via Pydantic v2, file size constraints, and lifespan model loading.\n"
        "3. Ingestion & Autofill Services: Dual-engine screenshot extraction (Anthropic Claude Vision primary and multi-stage Tesseract OCR fallback) alongside regex-based Quick Fill parsing.\n"
        "4. Machine Learning & Database Core (src/): Serialized scikit-learn pipeline (best_model.joblib), SHAP TreeExplainer local feature importance attribution, three-tier risk scoring, and persistent SQLite auditing (predictions.db)."
    )

    # Section 3
    h3 = doc.add_heading("3. Data & Feature Engineering Pipeline", level=1)
    h3.runs[0].font.color.rgb = navy

    doc.add_heading("3.1 Raw Profile Features (11 Dimensions)", level=2)
    doc.add_paragraph("The training dataset comprises 692 benchmark profile records (553 train, 139 hold-out test samples):")

    table1 = doc.add_table(rows=1, cols=5)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    table1.autofit = False

    headers = ["#", "Feature Name", "Data Type", "Permitted Range", "Definition / Calculation"]
    hdr_cells = table1.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "ECE9F8")
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.color.rgb = navy

    raw_features = [
        ("1", "profile pic", "int", "[0, 1]", "1 if custom avatar present; 0 if default placeholder."),
        ("2", "nums/length username", "float", "[0.0, 1.0]", "Ratio of numeric digits to username character length."),
        ("3", "fullname words", "int", ">= 0", "Word count in the account's display name."),
        ("4", "nums/length fullname", "float", "[0.0, 1.0]", "Ratio of numeric digits to display name length."),
        ("5", "name==username", "int", "[0, 1]", "1 if normalized full name equals username; 0 otherwise."),
        ("6", "description length", "int", ">= 0", "Character length of biography / description."),
        ("7", "external URL", "int", "[0, 1]", "1 if bio contains external URL / link; 0 otherwise."),
        ("8", "private", "int", "[0, 1]", "1 if account is private; 0 if public."),
        ("9", "#posts", "int", ">= 0", "Total lifetime published media/posts count."),
        ("10", "#followers", "int", ">= 0", "Total follower count."),
        ("11", "#follows", "int", ">= 0", "Total following count.")
    ]

    for row_data in raw_features:
        row = table1.add_row()
        for idx, val in enumerate(row_data):
            cell = row.cells[idx]
            cell.text = val
            cell.paragraphs[0].runs[0].font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    doc.add_heading("3.2 Engineered Features (4 Dimensions)", level=2)
    doc.add_paragraph("Derived dynamically at inference time in src/features.py:")
    doc.add_paragraph("• follower_following_ratio = #followers / (#follows + 1)", style='List Bullet')
    doc.add_paragraph("• posts_to_followers_ratio = #posts / (#followers + 1)", style='List Bullet')
    doc.add_paragraph("• username_to_fullname_digit_diff = (nums/length username) - (nums/length fullname)", style='List Bullet')
    doc.add_paragraph("• has_bio = 1 if description length > 0 else 0", style='List Bullet')

    # Section 4
    h4 = doc.add_heading("4. Screenshot Autofill & OCR Extraction Architecture", level=1)
    h4.runs[0].font.color.rgb = navy

    doc.add_paragraph(
        "The screenshot extraction service processes profile screenshots strictly in RAM (io.BytesIO) and never writes "
        "uploaded image bytes to disk, logs, or databases. The system supports two extraction backends controlled by SCREENSHOT_BACKEND:"
    )

    doc.add_paragraph("1. Anthropic Claude Vision Backend (Primary):", style='List Bullet')
    doc.add_paragraph(
        "Activated automatically when ANTHROPIC_API_KEY is configured. Uses the Anthropic SDK with model CLAUDE_MODEL "
        "(default: claude-3-haiku-20240307). Sends in-memory base64 encoded bytes with a strict JSON system prompt. "
        "Validates data types, clamps negative values, handles abbreviations (1.2K -> 1200, 3.4M -> 3400000), and rejects "
        "non-Instagram screenshots with a descriptive user message. A transparent privacy notice is displayed whenever this backend is used."
    )

    doc.add_paragraph("2. Multi-Stage Tesseract OCR Backend (Local Fallback):", style='List Bullet')
    doc.add_paragraph(
        "Executes 100% locally and offline without external API dependencies. Automatically handles mobile screenshots using 3 preprocessing pipelines:\n"
        "• Grayscale 2x upscale with autocontrast enhancement\n"
        "• Luminance inversion for Dark Mode screenshots\n"
        "• 3x upscale high-contrast thresholding\n"
        "Locates posts, followers, and following labels using fuzzy string matching (difflib >= 0.7) and extracts numeric bounding boxes "
        "located directly above (or beside) each label. Estimates avatar status (custom vs default silhouette) using pixel color variance "
        "and near-grey pixel ratios without facial recognition. Missing fields return null (never false zeros)."
    )

    # Section 5
    h5 = doc.add_heading("5. Model Evaluation & Benchmark Results", level=1)
    h5.runs[0].font.color.rgb = navy

    doc.add_paragraph("5.1 Champion Model Performance (Random Forest on Hold-out Test Set):")
    doc.add_paragraph("• Test Accuracy: 92.81%", style='List Bullet')
    doc.add_paragraph("• Test Precision: 95.38%", style='List Bullet')
    doc.add_paragraph("• Test Recall: 89.86%", style='List Bullet')
    doc.add_paragraph("• Test F1-Score: 92.54%", style='List Bullet')
    doc.add_paragraph("• Test ROC-AUC: 0.9812", style='List Bullet')
    doc.add_paragraph("• Test PR-AUC: 0.9801", style='List Bullet')

    doc.add_paragraph("5.2 5-Fold Stratified Cross-Validation Benchmark Comparison:")

    table2 = doc.add_table(rows=1, cols=7)
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    table2.autofit = False

    cv_headers = ["Model", "CV Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC", "Status"]
    for i, title in enumerate(cv_headers):
        cell = table2.rows[0].cells[i]
        cell.text = title
        set_cell_background(cell, "ECE9F8")
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = navy

    cv_rows = [
        ("Random Forest", "94.03%", "93.68%", "94.56%", "94.05%", "0.9869", "Champion"),
        ("Decision Tree", "91.69%", "92.17%", "91.31%", "91.66%", "0.9145", "Baseline"),
        ("Logistic Regression", "90.59%", "92.93%", "88.03%", "90.32%", "0.9724", "Linear Baseline"),
        ("SVM", "89.88%", "92.95%", "86.60%", "89.62%", "0.9634", "Kernel Baseline")
    ]

    for row_data in cv_rows:
        row = table2.add_row()
        for idx, val in enumerate(row_data):
            cell = row.cells[idx]
            cell.text = val
            cell.paragraphs[0].runs[0].font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Section 6
    h6 = doc.add_heading("6. REST API Reference", level=1)
    h6.runs[0].font.color.rgb = navy
    doc.add_paragraph("Interactive Swagger API documentation is served at: http://127.0.0.1:8000/docs")

    doc.add_paragraph("• GET /health - Reports model readiness, model name, and target column.", style='List Bullet')
    doc.add_paragraph("• POST /api/predict - Evaluates single profile JSON, returning predicted label, calibrated probability, risk tier, and top SHAP signed feature contributions.", style='List Bullet')
    doc.add_paragraph("• POST /api/screenshot/extract - In-memory OCR extraction returning backend_used, per-field confidence, warnings, and derived features.", style='List Bullet')
    doc.add_paragraph("• POST /api/quickfill/parse - Parses raw profile text and handles into structured counts and attributes.", style='List Bullet')
    doc.add_paragraph("• POST /api/quickfill/predict - Directly predicts authenticity from quick-fill parameters.", style='List Bullet')
    doc.add_paragraph("• POST /api/predict-batch - Evaluates multi-account CSV rosters with schema validation and summary metrics.", style='List Bullet')
    doc.add_paragraph("• GET /api/history & DELETE /api/history - Audits and clears prediction logs from SQLite.", style='List Bullet')

    # Section 7
    h7 = doc.add_heading("7. Setup & Execution Guide", level=1)
    h7.runs[0].font.color.rgb = navy

    doc.add_paragraph("Prerequisites: Windows 10/11, Python 3.10-3.12, Optional Tesseract OCR at C:\\Program Files\\Tesseract-OCR\\tesseract.exe")

    doc.add_paragraph("Execution Commands:")
    doc.add_paragraph("• Activate environment: .\\.venv\\Scripts\\Activate.ps1", style='List Bullet')
    doc.add_paragraph("• Install dependencies: pip install -r requirements.txt", style='List Bullet')
    doc.add_paragraph("• Launch Web Application: .\\run.ps1  (or python -m uvicorn app_api.main:app --host 127.0.0.1 --port 8000 --reload)", style='List Bullet')
    doc.add_paragraph("• Run Automated Pytest Suite: .\\run_tests.ps1  (or python -m pytest -v)", style='List Bullet')

    # Section 8
    h8 = doc.add_heading("8. Ethical Standards & Safe Deployment", level=1)
    h8.runs[0].font.color.rgb = navy
    doc.add_paragraph("1. Human-in-the-Loop Moderation: Predictions are statistical probabilities and should never serve as the sole criterion for punitive account bans or automated censorship.")
    doc.add_paragraph("2. Data Minimization: No user credentials, passwords, or personal account sessions are accessed or logged.")
    doc.add_paragraph("3. Zero Scraping: Eliminates live web scraping, preserving user privacy and adhering to platform acceptable use policies.")

    out_file = "DOCUMENTATION.docx"
    doc.save(out_file)
    print(f"Successfully generated {out_file}")

if __name__ == "__main__":
    create_document()

