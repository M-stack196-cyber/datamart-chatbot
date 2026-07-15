import fitz  # pymupdf
import docx

def extract_text(file_path: str) -> str:
    """Extract raw text from a PDF, DOCX, or TXT file."""
    if file_path.endswith(".pdf"):
        text = ""
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)

    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {file_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extract.py <path_to_file>")
        sys.exit(1)

    path = sys.argv[1]
    result = extract_text(path)
    print(f"--- Extracted {len(result)} characters ---")
    print(result[:500])
