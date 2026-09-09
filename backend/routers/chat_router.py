from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from services.rag_service import rag_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    question: str = Field(..., description="Pergunta do usuário a ser respondida com base nos PDFs.")
    top_k: Optional[int] = Field(default=4, ge=1, le=10, description="Número de trechos relevantes a serem buscados.")
    api_key: Optional[str] = Field(default=None, description="Chave de API enviada diretamente do frontend.")
    llm_provider: Optional[str] = Field(default="auto", description="Provedor de LLM desejado: 'gemini', 'openai', 'auto' ou 'fallback'.")
    model_name: Optional[str] = Field(default="gemini-1.5-flash", description="Nome do modelo Gemini/OpenAI desejado.")

class ValidateKeyRequest(BaseModel):
    api_key: str = Field(..., description="Chave de API a ser validada.")
    provider: str = Field(default="gemini", description="Provedor: 'gemini' ou 'openai'.")
    model_name: Optional[str] = Field(default="gemini-1.5-flash", description="Nome do modelo específico a ser testado.")

class GeminiModelsRequest(BaseModel):
    api_key: str = Field(..., description="Chave de API do Gemini.")

class SourceItem(BaseModel):
    source: str
    page: Any
    content_snippet: str
    similarity: Optional[float] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]

@router.post("", response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """Endpoint para processamento de perguntas RAG baseadas nos PDFs armazenados."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")

    try:
        result = rag_service.answer_question(
            query=request.question.strip(),
            top_k=request.top_k or 4,
            api_key=request.api_key,
            llm_provider=request.llm_provider or "auto",
            model_name=request.model_name or "gemini-1.5-flash"
        )
        return result
    except Exception as e:
        print(f"[Chat Router Error] Erro ao responder pergunta: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno no processamento RAG: {str(e)}")

@router.post("/validate-key")
async def validate_api_key(request: ValidateKeyRequest):
    """Endpoint para validar dinamicamente se a API Key do Gemini ou OpenAI é funcional."""
    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="Por favor, forneça uma chave de API para validar.")

    result = rag_service.validate_key(
        api_key=request.api_key.strip(),
        provider=request.provider,
        model_name=request.model_name or "gemini-1.5-flash"
    )
    return result

@router.post("/gemini-models")
async def list_gemini_models(request: GeminiModelsRequest):
    """Endpoint para listar os modelos do Gemini disponíveis para uma determinada API Key."""
    models = rag_service.get_available_gemini_models(request.api_key.strip())
    return {"models": models}
