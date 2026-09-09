from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from services.minio_service import minio_service
from routers import document_router, chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicialização e desligamento da aplicação."""
    print("==================================================")
    print(f"🚀 Iniciando {settings.PROJECT_NAME} (v{settings.VERSION})")
    print("==================================================")
    
    # Garantir que o bucket do MinIO existe
    try:
        minio_service.ensure_bucket_exists()
    except Exception as e:
        print(f"⚠️ AVISO: Não foi possível conectar ao MinIO na inicialização: {e}")
        
    yield
    print("🛑 Encerrando aplicação FastAPI...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API para Assistente RAG lendo PDFs do MinIO com indexação no ChromaDB",
    lifespan=lifespan
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os Roteadores
app.include_router(document_router.router)
app.include_router(chat_router.router)

@app.get("/health")
def health_check():
    """Endpoint para verificar a saúde da API."""
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "minio_endpoint": settings.MINIO_ENDPOINT,
        "chroma_mode": "embedded"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
