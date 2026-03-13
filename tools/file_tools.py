"""
J-RV-S File Tools — PDF & Document Analyzer
"""

import base64
import io

def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text[:8000]  # Limit to avoid token overflow
    except Exception as e:
        return f"PDF extraction error: {str(e)}"

def extract_text_file(file_bytes: bytes, filename: str) -> str:
    """Extract text from txt/csv/code files."""
    try:
        return file_bytes.decode("utf-8", errors="ignore")[:8000]
    except Exception as e:
        return f"File read error: {str(e)}"

def process_uploaded_file(file_bytes: bytes, filename: str, mime_type: str) -> dict:
    """Process any uploaded file and return content."""
    filename_lower = filename.lower()
    
    if mime_type == "application/pdf" or filename_lower.endswith(".pdf"):
        content = extract_pdf_text(file_bytes)
        return {"type": "pdf", "content": content, "filename": filename}
    
    elif any(filename_lower.endswith(ext) for ext in [".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".css"]):
        content = extract_text_file(file_bytes, filename)
        return {"type": "text", "content": content, "filename": filename}
    
    elif any(mime_type.startswith(t) for t in ["image/jpeg", "image/png", "image/gif", "image/webp"]):
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        return {"type": "image", "content": b64, "mime_type": mime_type, "filename": filename}
    
    else:
        return {"type": "unknown", "content": "Unsupported file type.", "filename": filename}
