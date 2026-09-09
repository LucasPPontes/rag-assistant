from typing import List, Dict, Any, Optional
from config import settings
from services.vector_service import vector_service
from services.minio_service import minio_service
import openai

# Suporte ao SDK oficial `google-genai` (idêntico ao assistente_seguradoras) e `google.generativeai`
HAS_GOOGLE_GENAI = False
HAS_GEMINI_OLD = False

try:
    from google import genai as new_genai
    HAS_GOOGLE_GENAI = True
except ImportError:
    pass

try:
    import google.generativeai as old_genai
    HAS_GEMINI_OLD = True
except ImportError:
    pass

class RAGService:
    def _call_gemini_api(self, api_key: str, prompt: str, target_model: str = "gemini-2.5-flash") -> Optional[str]:
        """Executa a chamada à API do Gemini usando o novo SDK `google-genai` ou o SDK tradicional com fallback de modelo."""
        key = api_key.strip()
        candidates = [target_model, "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        seen = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]

        # 1. Tentar usando o novo SDK `google-genai` (como no assistente_seguradoras)
        if HAS_GOOGLE_GENAI:
            for model_name in candidates:
                try:
                    client = new_genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if response and response.text:
                        print(f"[RAGService] Sucesso com `google-genai` no modelo '{model_name}'")
                        return response.text.strip()
                except Exception as e:
                    print(f"[RAGService] Tentativa com google-genai ('{model_name}') falhou: {e}")

        # 2. Fallback usando `google.generativeai` tradicional se o novo SDK não estiver presente ou falhar
        if HAS_GEMINI_OLD:
            for model_name in candidates:
                try:
                    old_genai.configure(api_key=key)
                    model = old_genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    if response and response.text:
                        print(f"[RAGService] Sucesso com `google.generativeai` no modelo '{model_name}'")
                        return response.text.strip()
                except Exception as e:
                    print(f"[RAGService] Tentativa com google.generativeai ('{model_name}') falhou: {e}")

        return None

    def answer_question(
        self, 
        query: str, 
        top_k: int = 4, 
        api_key: Optional[str] = None, 
        llm_provider: str = "auto",
        model_name: Optional[str] = "gemini-2.5-flash"
    ) -> Dict[str, Any]:
        """Realiza a busca por similaridade e gera a resposta usando a API Key informada dinamicamente ou do .env."""
        # Obtém a lista atualizada de arquivos realmente existentes no bucket do MinIO
        minio_files = set(f["filename"] for f in minio_service.list_files())

        search_results = vector_service.search(query, top_k=top_k, allowed_files=minio_files)

        if not search_results:
            return {
                "answer": "Nenhum documento foi encontrado no bucket do MinIO. Por favor, envie arquivos PDF na barra lateral para poder fazer perguntas sobre eles.",
                "sources": []
            }

        context_blocks = []
        sources = []
        for idx, item in enumerate(search_results, start=1):
            source_file = item["metadata"].get("source", "Desconhecido")
            page_num = item["metadata"].get("page", "?")
            content = item["content"]
            
            context_blocks.append(f"[Documento {idx} - Arquivo: {source_file}, Página: {page_num}]\n{content}")
            sources.append({
                "source": source_file,
                "page": page_num,
                "content_snippet": content[:250] + ("..." if len(content) > 250 else ""),
                "similarity": item.get("similarity")
            })

        formatted_context = "\n\n".join(context_blocks)

        system_instruction = (
            "Você é um assistente de Inteligência Artificial especializado em análise de documentos PDF e contratos.\n"
            "Sua missão é ajudar o usuário fornecendo respostas claras, didáticas, bem estruturadas e cordiais "
            "com base nos trechos fornecidos no CONTEXTO abaixo.\n\n"
            "DIRETRIZES DE RESPOSTA:\n"
            "1. Se a pergunta for ampla, genérica ou abrangente (ex: 'me fale sobre o arquivo', 'do que se trata este contrato?', 'resuma os documentos'), "
            "SINTETIZE E APRESENTE UM RESUMO EXECUTIVO dos documentos presentes no contexto. NUNCA recuse responder alegando que a pergunta é ampla.\n"
            "2. Se o contexto contiver mais de um documento/contrato distinto, liste e organize a resposta detalhando CADA UM DELES (ex: '📄 Documento 1: ...', '📄 Documento 2: ...').\n"
            "3. Destaque sempre dados principais como: Objeto do Contrato, Nomes das Partes/Empresas, Valores, Datas de Vigência e Cláusulas Importantes.\n"
            "4. Responda sempre em português do Brasil com ótima formatação markdown (listas, negritos e tópicos).\n"
        )

        prompt = (
            f"{system_instruction}\n\n"
            f"--- CONTEXTO DOS DOCUMENTOS ---\n{formatted_context}\n\n"
            f"--- PERGUNTA DO USUÁRIO ---\n{query}\n\n"
            "--- RESPOSTA E SÍNTESE ---"
        )

        answer = None
        provider = llm_provider.lower() if llm_provider else "auto"
        selected_model = model_name or "gemini-2.5-flash"

        gemini_key = api_key if (provider == "gemini" and api_key) else (api_key or settings.GEMINI_API_KEY)
        openai_key = api_key if (provider == "openai" and api_key) else (api_key or settings.OPENAI_API_KEY)

        # 1. Tentar Gemini se selecionado ou em 'auto'
        if (provider in ["gemini", "auto"]) and gemini_key and gemini_key.strip():
            answer = self._call_gemini_api(gemini_key, prompt, target_model=selected_model)

        # 2. Tentar OpenAI se resposta for None
        if answer is None and (provider in ["openai", "auto"]) and openai_key and openai_key.strip():
            try:
                client = openai.OpenAI(api_key=openai_key.strip())
                response = client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": "Você é um assistente de IA prestativo que responde perguntas com base em documentos PDF em português."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                answer = response.choices[0].message.content.strip()
                print(f"[RAGService] Resposta gerada via OpenAI ({settings.LLM_MODEL}).")
            except Exception as e:
                print(f"[RAGService Error] Falha ao chamar a API da OpenAI: {e}")

        # 3. Modo fallback/síntese local caso nenhuma chave tenha respondido
        if answer is None:
            answer = self._generate_fallback_answer(query, search_results)

        return {
            "answer": answer,
            "sources": sources
        }

    def validate_key(self, api_key: str, provider: str = "gemini", model_name: str = "gemini-2.5-flash") -> Dict[str, Any]:
        """Testa se a chave de API fornecida é válida fazendo uma requisição de teste."""
        if not api_key or not api_key.strip():
            return {"valid": False, "message": "A chave fornecida está vazia."}

        key = api_key.strip()
        provider_clean = provider.lower()

        if provider_clean in ["gemini", "google"]:
            test_prompt = "Teste de validação de chave. Responda 'OK'."
            test_ans = self._call_gemini_api(key, test_prompt, target_model=model_name)
            if test_ans:
                return {
                    "valid": True, 
                    "message": f"Chave Gemini API validada com sucesso! Conexão ativa ({model_name}).",
                    "available_models": self.get_available_gemini_models(key)
                }
            return {
                "valid": False, 
                "message": "Falha na validação do Gemini. A chave pode estar incorreta ou sem permissões de uso."
            }

        elif provider_clean == "openai":
            try:
                client = openai.OpenAI(api_key=key)
                client.models.list()
                return {"valid": True, "message": f"Chave OpenAI API validada com sucesso! Conexão ativa ({settings.LLM_MODEL})."}
            except Exception as e:
                return {"valid": False, "message": f"Chave da OpenAI inválida ou sem acesso: {str(e)[:120]}"}

        return {"valid": False, "message": f"Provedor '{provider}' não suportado para validação."}

    def get_available_gemini_models(self, api_key: str) -> List[str]:
        """Lista os modelos principais suportados pelo Gemini."""
        return ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

    def _generate_fallback_answer(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """Gera uma resposta síntese estruturada a partir dos trechos recuperados quando nenhuma API Key está disponível."""
        answer_parts = [
            "ℹ️ *(Modo Sem Chave LLM / Síntese Local)*\n",
            f"Com base na busca pelos trechos mais relevantes para a pergunta **\"{query}\"**, foram encontrados os seguintes fragmentos nos documentos:\n"
        ]

        for idx, item in enumerate(search_results, start=1):
            source_file = item["metadata"].get("source", "Desconhecido")
            page_num = item["metadata"].get("page", "?")
            snippet = item["content"].strip()
            answer_parts.append(f"**Trecho {idx} (Arquivo `{source_file}`, Pág. {page_num}):**\n> \"{snippet}\"\n")

        answer_parts.append("\n💡 *Dica: Insira sua Chave de API na barra lateral para habilitar respostas em tempo real com IA!*")
        return "\n".join(answer_parts)

rag_service = RAGService()
