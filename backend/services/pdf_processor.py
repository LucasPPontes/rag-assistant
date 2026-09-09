import io
from typing import List, Dict, Any
from pypdf import PdfReader

class DocumentChunk:
    def __init__(self, page_content: str, metadata: Dict[str, Any]):
        self.page_content = page_content
        self.metadata = metadata

class PDFProcessor:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_text(self, text: str) -> List[str]:
        """Divisão recursiva leve de texto sem dependência de bibliotecas pesadas."""
        if not text:
            return []
            
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            if end >= text_length:
                chunks.append(text[start:])
                break
                
            # Tenta quebrar em limites de parágrafo, quebra de linha ou espaço
            cut = text.rfind("\n\n", start, end)
            if cut == -1 or cut < start + 200:
                cut = text.rfind("\n", start, end)
            if cut == -1 or cut < start + 200:
                cut = text.rfind(" ", start, end)
            if cut == -1 or cut < start:
                cut = end

            chunks.append(text[start:cut].strip())
            start = max(cut - self.chunk_overlap, start + 1)
            
        return [c for c in chunks if c.strip()]

    def process_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> List[DocumentChunk]:
        """Lê os bytes de um PDF, extrai o texto página por página e gera chunks levemente."""
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        all_chunks = []
        chunk_counter = 0

        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                page_chunks = self._split_text(page_text)
                for chunk_text in page_chunks:
                    doc = DocumentChunk(
                        page_content=chunk_text,
                        metadata={
                            "source": filename,
                            "page": page_idx + 1,
                            "chunk_id": f"{filename}_page_{page_idx + 1}_idx_{chunk_counter}"
                        }
                    )
                    all_chunks.append(doc)
                    chunk_counter += 1
        
        print(f"[PDFProcessor] '{filename}' processado: {len(reader.pages)} páginas -> {len(all_chunks)} chunks.")
        return all_chunks

pdf_processor = PDFProcessor()
