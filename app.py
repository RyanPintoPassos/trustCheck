import streamlit as st
import base64
import os

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from duckduckgo_search import DDGS

# =========================
# CONFIG
# =========================

GROQ_API_KEY = os.getenv("GROQ877777")

st.set_page_config(
    page_title="TrustCheck",
    page_icon="🛡️",
    layout="centered"
)

# =========================
# VALIDAÇÃO API KEY
# =========================

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY não encontrada nas variáveis do Streamlit.")
    st.stop()

# =========================
# MODELOS
# =========================

vision_llm = ChatGroq(
    model_name="meta-llama/llama-4-scout-17b-16e-instruct",
    groq_api_key=GROQ_API_KEY,
)

text_llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY,
    temperature=0.1
)

# =========================
# BUSCA WEB
# =========================

def buscar(query):
    try:
        with DDGS(timeout=20) as ddgs:

            resultados = list(
                ddgs.text(
                    query,
                    max_results=3
                )
            )

            if not resultados:
                return "Nenhum resultado encontrado."

            textos = []

            for r in resultados:

                titulo = r.get("title", "")
                body = r.get("body", "")

                textos.append(f"{titulo} - {body}")

            return "\n".join(textos)

    except Exception as e:
        return f"Erro na busca web: {str(e)}"

# =========================
# UI
# =========================

st.title("🛡️ Sistema de Validação e Segurança Digital")

st.markdown("""
**Verifique a veracidade de notícias, detecte links suspeitos
e identifique conteúdo gerado por IA.**
""")

tab1, tab2 = st.tabs(["📝 Texto ou Link", "🖼️ Print / Imagem"])

input_texto = ""

# =========================
# ABA TEXTO
# =========================

with tab1:

    input_texto = st.text_area(
        "Cole a notícia, o texto viral ou o link aqui:",
        height=150,
        placeholder="Ex: 'Urgente! Clique aqui para resgatar seu prêmio...'"
    )

# =========================
# ABA IMAGEM
# =========================

with tab2:

    foto = st.file_uploader(
        "Suba o print da notícia ou imagem suspeita:",
        type=["png", "jpg", "jpeg"]
    )

    if foto is None and "conteudo_extraido" in st.session_state:
        del st.session_state["conteudo_extraido"]

    if foto:

        st.image(foto, width=300)

        if st.button("Analisar Imagem"):

            with st.spinner("Analisando imagem com IA Visual..."):

                try:

                    img_base64 = base64.b64encode(
                        foto.getvalue()
                    ).decode()

                    msg = vision_llm.invoke([
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """
Faça duas coisas:

1. Transcreva todo o texto legível da imagem.
Se NÃO houver texto, escreva:
[TEXTO EXTRAÍDO]: Nenhum texto na imagem

2. Analise visualmente:
- descreva brevemente a cena
- diga se há sinais de manipulação
- diga se parece IA

Formato obrigatório:

[TEXTO EXTRAÍDO]: ...
[ANÁLISE VISUAL]: ...
"""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_base64}"
                                    }
                                }
                            ]
                        }
                    ])

                    st.session_state["conteudo_extraido"] = msg.content

                    st.success("Análise visual concluída!")

                    with st.expander("Resultado da análise visual"):
                        st.write(msg.content)

                except Exception as e:
                    st.error(f"Erro ao analisar imagem: {e}")

# =========================
# CONTEÚDO FINAL
# =========================

conteudo_final = (
    input_texto.strip()
    if input_texto.strip()
    else st.session_state.get("conteudo_extraido", "")
)

st.divider()

# =========================
# BOTÃO PRINCIPAL
# =========================

if st.button(
    "🚀 ANALISAR CONFIABILIDADE E SEGURANÇA",
    use_container_width=True
):

    if not conteudo_final:

        st.error(
            "Insira um texto/link ou analise uma imagem primeiro."
        )

    else:

        with st.spinner(
            "Cruzando dados, pesquisando fontes e analisando..."
        ):

            try:

                # =========================
                # BUSCA WEB
                # =========================

                if "Nenhum texto na imagem" in conteudo_final:

                    resultados_web = """
Busca ignorada:
A imagem não contém texto suficiente.
"""

                else:

                    query_base = (
                        conteudo_final[:120]
                        .replace("\n", " ")
                    )

                    query = f"""
{query_base}
site:g1.globo.com OR
site:uol.com.br OR
site:cnnbrasil.com.br
"""

                    resultados_web = buscar(query)

                # =========================
                # PROMPT
                # =========================

                template = """
Você é um Especialista em Segurança Digital,
Fact-Checking e Educação Midiática.

CONTEÚDO:
{conteudo}

RESULTADOS DA BUSCA:
{resultados}

Faça:

1. Verificação de fatos
2. Detecção de golpes
3. Linguagem manipulativa
4. Sinais de IA
5. Análise visual

Retorne EXATAMENTE nesse formato markdown:

### 🎯 RESULTADO FINAL
- **PONTUAÇÃO:** [0-100]
- **CLASSIFICAÇÃO:** [Confiável, Duvidoso ou Perigoso]

### 🚨 SISTEMA DE ALERTAS
- Liste alertas relevantes

### 🔎 ANÁLISE DETALHADA
- Fatos e Fontes
- Segurança e Links
- Análise Visual / IA

### 📝 CONCLUSÃO TÉCNICA
- Explique a classificação

### 💡 APRENDA A IDENTIFICAR
- Dica educativa
"""

                prompt = PromptTemplate.from_template(template)

                chain = prompt | text_llm

                analise = chain.invoke({
                    "conteudo": conteudo_final,
                    "resultados": resultados_web
                })

                st.success("Análise concluída!")

                st.markdown(analise.content)

                # DEBUG OPCIONAL
                with st.expander("Resultados da busca web"):
                    st.write(resultados_web)

            except Exception as e:

                st.error(f"Erro geral: {e}")