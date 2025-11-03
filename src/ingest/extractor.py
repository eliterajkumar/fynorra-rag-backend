"""Text extraction from PDF and HTML files."""
import pdfplumber
import requests
from bs4 import BeautifulSoup
from typing import Optional, List
from io import BytesIO

# Try PyMuPDF for faster PDF extraction
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> List[str]:
    """
    Extract text from PDF file content, returning one string per page.
    
    Args:
        pdf_bytes: PDF file content as bytes
    
    Returns:
        List[str]: One string per page (page 1 to page N)
    """
    pages = []
    
    if HAS_FITZ:
        # Use PyMuPDF for speed
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                page_text = page.get_text("text")
                if page_text.strip():
                    pages.append(page_text.strip())
            doc.close()
            if pages:
                return pages
        except Exception:
            # Fallback to pdfplumber if PyMuPDF fails
            pass
    
    # Fallback to pdfplumber
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                pages.append(page_text.strip())
    
    # Ensure at least one page returned
    if not pages:
        return [""]
    
    return pages


def extract_text_from_pdf(file_content: bytes) -> str:
    """Legacy function: Extract text from PDF file content (returns single string)."""
    pages = extract_text_from_pdf_bytes(file_content)
    return "\n\n".join(pages)


def extract_text_from_html(url_or_html: str, base_url: Optional[str] = None) -> List[str]:
    """
    Extract text from HTML content, returning sections/pages.
    
    Args:
        url_or_html: URL string (starting with http) or raw HTML string
        base_url: Optional base URL for resolving relative links
    
    Returns:
        List[str]: Sections of text (at minimum [clean_text])
    """
    html_content = url_or_html
    
    # If it looks like a URL, fetch it
    if url_or_html.startswith(("http://", "https://")):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url_or_html, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    # Try to extract main content (article, main, or body)
    main_content = soup.find("article") or soup.find("main") or soup.find("body")
    if not main_content:
        main_content = soup
    
    # Extract text and split into sections (paragraphs)
    sections = []
    
    # Split by paragraphs or headings
    for element in main_content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "div"]):
        text = element.get_text(separator=" ", strip=True)
        if text and len(text) > 20:  # Filter out very short sections
            sections.append(text)
    
    # If no sections found, get all text
    if not sections:
        text = main_content.get_text(separator=" ", strip=True)
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in chunks if chunk)
        if clean_text:
            sections = [clean_text]
    
    # Ensure at least one section
    if not sections:
        sections = [""]
    
    return sections


def extract_text_from_url(url: str) -> tuple[List[str], Optional[str]]:
    """
    Scrape URL and extract text content as page sections.
    
    Returns:
        tuple: (List[str] of sections, Optional[str] title)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    html_content = response.text
    
    # Extract title if available
    soup = BeautifulSoup(html_content, "html.parser")
    title = soup.title.string if soup.title else None
    
    sections = extract_text_from_html(html_content)
    return sections, title


def extract_text_from_file(file_content: bytes, file_type: str) -> str:
    """
    Legacy function: Extract text from file based on file type (returns single string).
    """
    if file_type == "pdf" or file_type.endswith(".pdf"):
        return extract_text_from_pdf(file_content)
    elif file_type in ["html", "htm"] or file_type.endswith((".html", ".htm")):
        sections = extract_text_from_html(file_content.decode("utf-8", errors="ignore"))
        return "\n\n".join(sections)
    elif file_type in ["txt", "text"] or file_type.endswith(".txt"):
        return file_content.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

