MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
EXTENSIONS = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown"}


class DocumentRejected(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def file_extension(filename: str) -> str:
    dot = filename.rfind(".")
    extension = filename[dot:].lower() if dot >= 0 else ""
    if extension not in EXTENSIONS:
        raise DocumentRejected(415, "Upload a PDF, TXT or Markdown file.")
    return extension


def _pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF-"):
        raise DocumentRejected(422, "This file is not a valid PDF.")
    import pymupdf  # A large library, needed only when a PDF is uploaded.

    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.needs_pass:
                raise DocumentRejected(422, "Password-protected PDFs are not supported.")
            return "\n".join(page.get_text() for page in document)
    except DocumentRejected:
        raise
    except Exception as exc:  # PyMuPDF raises several types for damaged files.
        raise DocumentRejected(422, "This PDF could not be read.") from exc


def extract_text(extension: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise DocumentRejected(413, "Files can be up to 10 MB.")
    if extension == ".pdf":
        text = _pdf_text(data)
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentRejected(422, "Text files must be UTF-8.") from exc
    text = text.replace("\x00", "").strip()
    if not text:
        raise DocumentRejected(422, "No readable text found. Scanned PDFs are not supported yet.")
    return text[:MAX_TEXT_CHARS]
