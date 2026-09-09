from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from services.minio_service import minio_service
from services.pdf_processor import pdf_processor
from services.vector_service import vector_service

router = APIRouter(prefix="/api/documents", tags=["Documents"])

def process_and_index_file(filename: str, pdf_bytes: bytes):
    """Função auxiliar para extrair texto e indexar no ChromaDB."""
    chunks = pdf_processor.process_pdf_bytes(pdf_bytes, filename)
    if chunks:
        vector_service.index_documents(filename, chunks)

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Faz upload de um arquivo PDF para o MinIO e dispara a indexação no ChromaDB."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos.")

    content = await file.read()
    
    # 1. Enviar para o MinIO
    minio_service.upload_file(file.filename, content, content_type="application/pdf")
    
    # 2. Processar e Indexar no Vector Store
    chunks_count = 0
    try:
        chunks = pdf_processor.process_pdf_bytes(content, file.filename)
        if chunks:
            chunks_count = vector_service.index_documents(file.filename, chunks)
    except Exception as e:
        print(f"[Upload Router Error] Erro ao indexar PDF {file.filename}: {e}")

    return {
        "message": f"Arquivo '{file.filename}' enviado e indexado com sucesso.",
        "filename": file.filename,
        "chunks_indexed": chunks_count
    }

@router.get("", response_model=List[Dict[str, Any]])
async def list_documents():
    """Lista todos os arquivos no MinIO e indica se estão indexados no ChromaDB."""
    files_in_minio = minio_service.list_files()
    indexed_files = vector_service.get_indexed_files()

    result = []
    for file_info in files_in_minio:
        fname = file_info["filename"]
        result.append({
            "filename": fname,
            "size": file_info["size"],
            "last_modified": file_info["last_modified"],
            "is_indexed": fname in indexed_files
        })
    return result

@router.post("/sync")
async def sync_all_documents():
    """Lê todos os PDFs armazenados no MinIO e garante que todos estão indexados no ChromaDB."""
    minio_files = minio_service.list_files()
    indexed_files = vector_service.get_indexed_files()
    
    processed_count = 0
    total_chunks = 0

    for file_info in minio_files:
        filename = file_info["filename"]
        if filename.endswith(".pdf"):
            try:
                pdf_bytes = minio_service.get_file_bytes(filename)
                chunks = pdf_processor.process_pdf_bytes(pdf_bytes, filename)
                if chunks:
                    c_count = vector_service.index_documents(filename, chunks)
                    total_chunks += c_count
                    processed_count += 1
            except Exception as e:
                print(f"[Sync Error] Falha ao processar {filename}: {e}")

    return {
        "message": f"Sincronização concluída com sucesso.",
        "files_processed": processed_count,
        "total_chunks_indexed": total_chunks
    }

@router.delete("/{filename}")
async def delete_document(filename: str):
    """Remove o arquivo do MinIO e exclui seus vetores do ChromaDB."""
    minio_deleted = minio_service.delete_file(filename)
    vector_deleted = vector_service.delete_document_embeddings(filename)

    if not minio_deleted and not vector_deleted:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado ou erro ao remover.")

    return {
        "message": f"Arquivo '{filename}' e seus vetores foram removidos.",
        "filename": filename
    }
