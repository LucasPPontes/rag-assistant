import os
import requests
import streamlit as st

# Configuração da página Streamlit
st.set_page_config(
    page_title="Assistente RAG - MinIO & FastAPI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL padrão do Backend
DEFAULT_BACKEND = os.getenv("BACKEND_URL", "http://backend:8001")

def get_backend_url():
    """Retorna dinamicamente a URL ativa do backend (http://backend:8001 no Docker ou http://localhost:8001 local)."""
    try:
        r = requests.get(f"{DEFAULT_BACKEND}/health", timeout=1.5)
        if r.status_code == 200:
            return DEFAULT_BACKEND
    except Exception:
        pass
    return "http://localhost:8001"

# Estilos CSS Customizados para Visual Moderno e Elegante
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e0e6ed;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e2640 0%, #0d1b2a 100%);
        padding: 1.8rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        margin-bottom: 1.5rem;
        border: 1px solid #2a365c;
    }
    
    .main-header h1 {
        color: #4cc9f0;
        font-weight: 700;
        margin: 0;
        font-size: 2.2rem;
    }

    .main-header p {
        color: #94a3b8;
        margin-top: 0.4rem;
        font-size: 1rem;
    }

    .source-card {
        background: #161b26;
        border-left: 4px solid #4cc9f0;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 8px;
        margin-bottom: 8px;
        font-size: 0.88rem;
        color: #cbd5e1;
    }
    
    .source-tag {
        background-color: #1e293b;
        color: #38bdf8;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.78rem;
    }

    .badge-indexed {
        background-color: #065f46;
        color: #34d399;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-pending {
        background-color: #92400e;
        color: #fbbf24;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
</style>
""", unsafe_allow_html=True)

# Funções de Comunicação com a API
def fetch_documents():
    backend = get_backend_url()
    try:
        res = requests.get(f"{backend}/api/documents", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Erro ao conectar ao backend ({backend}): {e}")
    return []

def upload_pdf_file(file):
    backend = get_backend_url()
    try:
        files = {"file": (file.name, file.getvalue(), "application/pdf")}
        res = requests.post(f"{backend}/api/documents/upload", files=files, timeout=30)
        return res
    except Exception as e:
        return None

def delete_pdf_file(filename):
    backend = get_backend_url()
    try:
        res = requests.delete(f"{backend}/api/documents/{filename}", timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def sync_documents():
    backend = get_backend_url()
    try:
        res = requests.post(f"{backend}/api/documents/sync", timeout=30)
        return res
    except Exception:
        return None

def validate_api_key(api_key, provider="gemini", model_name="gemini-1.5-flash"):
    backend = get_backend_url()
    try:
        payload = {"api_key": api_key, "provider": provider, "model_name": model_name}
        res = requests.post(f"{backend}/api/chat/validate-key", json=payload, timeout=15)
        if res.status_code == 200:
            return res.json()
        return {"valid": False, "message": f"Erro do servidor ({res.status_code}): {res.text}"}
    except Exception as e:
        return {"valid": False, "message": f"Falha ao conectar no servidor ({backend}): {e}"}

def fetch_gemini_models(api_key):
    backend = get_backend_url()
    try:
        payload = {"api_key": api_key}
        res = requests.post(f"{backend}/api/chat/gemini-models", json=payload, timeout=10)
        if res.status_code == 200:
            return res.json().get("models", [])
    except Exception:
        pass
    return ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

def send_chat_query(question, top_k=4, api_key=None, llm_provider="auto", model_name="gemini-1.5-flash"):
    backend = get_backend_url()
    try:
        payload = {
            "question": question, 
            "top_k": top_k,
            "api_key": api_key if (api_key and api_key.strip()) else None,
            "llm_provider": llm_provider,
            "model_name": model_name
        }
        res = requests.post(f"{backend}/api/chat", json=payload, timeout=45)
        if res.status_code == 200:
            return res.json()
        else:
            return {"answer": f"⚠️ Erro no backend: {res.text}", "sources": []}
    except Exception as e:
        return {"answer": f"⚠️ Falha na comunicação com o backend ({backend}): {e}", "sources": []}

# --- SIDEBAR: Gerenciamento de PDFs & Configuração de API Key ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/pdf-2.png", width=55)
    st.title("Painel de Controle")
    st.caption("MinIO S3 & Configuração de IA")
    st.divider()

    # --- SEÇÃO 1: CONFIGURAÇÃO DE LLM / API KEY ---
    st.subheader("🔑 Validação de Chave & Modelo")
    
    llm_choice = st.selectbox(
        "Escolha o Provedor de IA:",
        ["Google Gemini (Gratuito)", "OpenAI (GPT-4o/GPT-3.5)", "Síntese Local (Sem Key)"],
        index=0
    )

    user_api_key = ""
    llm_provider_code = "auto"
    selected_gemini_model = "gemini-1.5-flash"

    if llm_choice == "Google Gemini (Gratuito)":
        llm_provider_code = "gemini"
        user_api_key = st.text_input(
            "Digite sua Gemini API Key:", 
            type="password", 
            placeholder="AIzaSy...",
            help="Obtenha uma chave grátis no Google AI Studio: https://aistudio.google.com/"
        )

        default_gemini_options = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash-8b"]
        
        if "custom_gemini_models" in st.session_state and st.session_state.custom_gemini_models:
            gemini_options = st.session_state.custom_gemini_models
        else:
            gemini_options = default_gemini_options

        selected_gemini_model = st.selectbox(
            "Selecione a versão do Gemini:",
            gemini_options,
            index=0,
            help="Escolha o modelo do Gemini ativado na sua chave de API"
        )

    elif llm_choice == "OpenAI (GPT-4o/GPT-3.5)":
        llm_provider_code = "openai"
        user_api_key = st.text_input(
            "Digite sua OpenAI API Key:", 
            type="password",
            placeholder="sk-...",
            help="Obtenha sua chave no painel da OpenAI"
        )
    else:
        llm_provider_code = "fallback"
        st.info("🟡 Modo Síntese Local Ativo (Exibe trechos dos PDFs sem chamar IA externa).")

    # BOTÃO DE VALIDAÇÃO DE CHAVE DE ATIVAÇÃO
    if llm_choice != "Síntese Local (Sem Key)":
        if st.button("⚡ Validar Chave de Ativação", use_container_width=True):
            if not user_api_key.strip():
                st.warning("⚠️ Por favor, digite uma chave de API para validar.")
            else:
                with st.spinner("Validando chave e listando modelos disponíveis..."):
                    val_res = validate_api_key(
                        user_api_key, 
                        provider=llm_provider_code,
                        model_name=selected_gemini_model
                    )
                    if val_res.get("valid"):
                        st.success(f"✅ {val_res.get('message')}")
                        if "available_models" in val_res and val_res["available_models"]:
                            st.session_state.custom_gemini_models = val_res["available_models"]
                            st.info(f"📋 Modelos detectados: `{', '.join(val_res['available_models'][:5])}`")
                    else:
                        st.error(f"❌ {val_res.get('message')}")

    st.divider()

    # --- SEÇÃO 2: UPLOAD & ARQUIVOS NO MINIO ---
    st.subheader("📤 Enviar PDF para MinIO")
    uploaded_file = st.file_uploader("Selecione um arquivo PDF", type=["pdf"])
    if uploaded_file is not None:
        if st.button("🚀 Upload & Indexar no MinIO", use_container_width=True):
            with st.spinner("Enviando para o MinIO e gerando embeddings..."):
                response = upload_pdf_file(uploaded_file)
                if response and response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ {data.get('message', 'Upload concluído!')}")
                    st.rerun()
                else:
                    st.error("❌ Erro ao enviar o arquivo.")

    st.divider()

    # Sincronização e Refresh
    col_sync, col_ref = st.columns([2, 1])
    with col_sync:
        if st.button("🔄 Sincronizar Tudo", help="Sincroniza todos os PDFs do MinIO", use_container_width=True):
            with st.spinner("Sincronizando..."):
                sync_documents()
                st.success("Sincronizado!")
                st.rerun()
    with col_ref:
        if st.button("🔄 Atualizar", help="Recarrega lista de documentos", use_container_width=True):
            st.rerun()

    st.subheader("📄 PDFs no Bucket")
    documents = fetch_documents()

    if not documents:
        st.info("Nenhum PDF encontrado no bucket do MinIO.")
    else:
        for doc in documents:
            fname = doc["filename"]
            is_idx = doc.get("is_indexed", False)
            size_kb = round(doc.get("size", 0) / 1024, 1)
            
            with st.expander(f"📄 {fname} ({size_kb} KB)"):
                if is_idx:
                    st.markdown('<span class="badge-indexed">✓ Indexado no ChromaDB</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge-pending">⏳ Não Indexado</span>', unsafe_allow_html=True)
                
                st.write(f"**Modificado:** {doc.get('last_modified', 'N/A')[:19] if doc.get('last_modified') else 'N/A'}")
                
                if st.button(f"🗑️ Deletar", key=f"del_{fname}", use_container_width=True):
                    if delete_pdf_file(fname):
                        st.success(f"Deletado: {fname}")
                        st.rerun()
                    else:
                        st.error("Erro ao deletar arquivo.")

    st.divider()
    st.caption(f"🔌 Backend Conectado: `{get_backend_url()}`")

# --- ÁREA PRINCIPAL DE CHAT ---
st.markdown("""
<div class="main-header">
    <h1>🤖 Assistente RAG com MinIO & Gemini AI</h1>
    <p>Faça perguntas sobre os contratos e documentos PDF armazenados no seu MinIO S3.</p>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Olá! Sou seu assistente RAG. Insira sua **Chave de Ativação** na barra lateral, selecione o modelo do Gemini desejado e clique em **⚡ Validar Chave**!",
            "sources": []
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message.get("sources"):
            with st.expander("📚 Fontes e Trechos Utilizados do PDF"):
                for idx, src in enumerate(message["sources"], start=1):
                    similarity_text = f" | Similaridade: {src['similarity']*100:.1f}%" if src.get("similarity") else ""
                    st.markdown(f"""
                    <div class="source-card">
                        <span class="source-tag">Fonte #{idx}</span> 
                        <strong>Arquivo:</strong> <code>{src['source']}</code> | <strong>Página:</strong> {src['page']}{similarity_text}
                        <br/><br/>
                        <em>"{src['content_snippet']}"</em>
                    </div>
                    """, unsafe_allow_html=True)

if user_input := st.chat_input("Digite sua pergunta sobre os documentos..."):
    st.session_state.messages.append({"role": "user", "content": user_input, "sources": []})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner(f"Consultando PDFs no MinIO e gerando resposta com {selected_gemini_model if llm_provider_code=='gemini' else 'IA'}..."):
            response_data = send_chat_query(
                question=user_input,
                top_k=4,
                api_key=user_api_key,
                llm_provider=llm_provider_code,
                model_name=selected_gemini_model
            )
            answer = response_data.get("answer", "Desculpe, ocorreu um erro ao gerar a resposta.")
            sources = response_data.get("sources", [])
            
            st.markdown(answer)
            
            if sources:
                with st.expander("📚 Fontes e Trechos Utilizados do PDF"):
                    for idx, src in enumerate(sources, start=1):
                        similarity_text = f" | Similaridade: {src['similarity']*100:.1f}%" if src.get("similarity") else ""
                        st.markdown(f"""
                        <div class="source-card">
                            <span class="source-tag">Fonte #{idx}</span> 
                            <strong>Arquivo:</strong> <code>{src['source']}</code> | <strong>Página:</strong> {src['page']}{similarity_text}
                            <br/><br/>
                            <em>"{src['content_snippet']}"</em>
                        </div>
                        """, unsafe_allow_html=True)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources
    })
