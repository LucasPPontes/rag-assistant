from typing import List, Dict, Any, Set, Optional
import math
import chromadb
from config import settings
from services.pdf_processor import DocumentChunk
import openai

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

class VectorService:
    def __init__(self):
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            print("[VectorService] Inicializando ChromaDB embutido (PersistentClient em ./chroma_db)...")
            self._client = chromadb.PersistentClient(path="./chroma_db")
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings via Gemini API ou OpenAI API de forma ultraleve e sem PyTorch."""
        if not texts:
            return []

        if HAS_GEMINI and settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip() != "":
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY.strip())
                res = genai.embed_content(
                    model="models/text-embedding-004",
                    content=texts
                )
                if isinstance(res, dict) and "embedding" in res:
                    return [res["embedding"]]
                elif isinstance(res, dict) and "embedding" in res.get("embedding", []):
                    return [e["values"] for e in res["embedding"]]
                elif hasattr(res, "embedding"):
                    if isinstance(res.embedding[0], list):
                        return res.embedding
                    return [res.embedding]
            except Exception as e:
                print(f"[VectorService Error] Erro nos embeddings do Gemini: {e}")

        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() != "":
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY.strip())
                resp = client.embeddings.create(
                    input=texts,
                    model="text-embedding-3-small"
                )
                return [data.embedding for data in resp.data]
            except Exception as e:
                print(f"[VectorService Error] Erro nos embeddings da OpenAI: {e}")

        return [self._lightweight_hash_embedding(text) for text in texts]

    def _lightweight_hash_embedding(self, text: str, dim: int = 128) -> List[float]:
        """Gera um vetor normalizado simples por Hashing para execução sem API key e sem PyTorch."""
        vec = [0.0] * dim
        words = text.lower().split()
        if not words:
            return vec
        for word in words:
            h = hash(word) % dim
            vec[h] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def index_documents(self, filename: str, documents: List[DocumentChunk]) -> int:
        """Deleta embeddings anteriores do mesmo arquivo e adiciona os novos chunks."""
        if not documents:
            return 0

        self.delete_document_embeddings(filename)

        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        ids = [doc.metadata.get("chunk_id", f"{filename}_chunk_{i}") for i, doc in enumerate(documents)]

        embeddings_list = self._get_embeddings(texts)

        self.collection.add(
            ids=ids,
            embeddings=embeddings_list,
            documents=texts,
            metadatas=metadatas
        )

        print(f"[VectorService] Indexados {len(documents)} chunks para '{filename}'.")
        return len(documents)

    def search(self, query: str, top_k: int = 4, allowed_files: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """Realiza busca vetorial por similaridade no ChromaDB filtrando apenas arquivos presentes no MinIO."""
        # Se uma lista de arquivos permitidos for informada e estiver vazia, retorna vazio imediatamente
        if allowed_files is not None and len(allowed_files) == 0:
            print("[VectorService] O bucket do MinIO está vazio. Busca abortada.")
            return []

        query_embeddings = self._get_embeddings([query])
        if not query_embeddings:
            return []
        
        # Pega mais resultados inicialmente se precisarmos filtrar
        fetch_k = top_k * 3 if allowed_files is not None else top_k
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=fetch_k
        )

        documents_found = []
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

            for text, meta, dist in zip(docs, metadatas, distances):
                source_name = meta.get("source") if meta else None
                # Se allowed_files estiver definido, filtra apenas trechos de arquivos atualmente existentes no MinIO
                if allowed_files is not None and source_name not in allowed_files:
                    continue

                similarity_score = round(1 - dist, 4) if dist is not None else None
                documents_found.append({
                    "content": text,
                    "metadata": meta,
                    "similarity": similarity_score
                })

                if len(documents_found) >= top_k:
                    break

        return documents_found

    def delete_document_embeddings(self, filename: str) -> bool:
        """Deleta todos os chunks indexados de um arquivo específico."""
        try:
            self.collection.delete(where={"source": filename})
            print(f"[VectorService] Embeddings de '{filename}' removidos.")
            return True
        except Exception as e:
            print(f"[VectorService Warning] Erro ao remover embeddings de '{filename}': {e}")
            return False

    def get_indexed_files(self) -> Set[str]:
        """Retorna os nomes dos arquivos que possuem trechos indexados no ChromaDB."""
        try:
            data = self.collection.get(include=["metadatas"])
            if not data or not data.get("metadatas"):
                return set()
            
            indexed_sources = set()
            for meta in data["metadatas"]:
                if meta and "source" in meta:
                    indexed_sources.add(meta["source"])
            return indexed_sources
        except Exception as e:
            print(f"[VectorService Error] Erro ao listar arquivos indexados: {e}")
            return set()

vector_service = VectorService()
