import streamlit as st
import base64
import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from duckduckgo_search import DDGS

# 1. Configuração da Página
st.set_page_config(
    page_title="TrustCheck - Validador", 
    page_icon="🛡️", 
    layout="centered"
)

# 2. Configuração da Chave API
# Dica: No Streamlit Cloud, coloque a chave em Settings > Secrets
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY == "SUA_CHAVE_API_AQUI":
    st.warning("⚠️ Chave da Groq não encontrada. Configure a GROQ_API_KEY no servidor ou no código.")

# 3. Inicialização dos Modelos de IA
try:
    vision_llm = ChatGroq(
        model_name="llama-3.2-11b-vision-preview", # Modelo de visão atualizado e estável
        groq_api_key=GROQ_API_KEY
    )

    text_llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",
        groq_api_key=GROQ_API_KEY,
        temperature=0.1
    )
except Exception as e:
    st.error(f"Erro ao inicializar os modelos: {e}")

# 4. Função de Busca Aprimorada (Forçando IP/Região Brasil)
def buscar_web(query):
    """Busca no DuckDuckGo forçando resultados brasileiros para evitar discrepâncias do Streamlit Cloud"""
    try:
        with DDGS() as ddgs:
            # 1ª Tentativa: Busca focada nos sites de notícia
            resultados = list(ddgs.text(query, region="br-pt", max_results=5))
            
            # 2ª Tentativa (Fallback): Se a busca restrita não achar nada, tenta a busca aberta
            if not resultados:
                query_aberta = query.split("site:")[0].strip()
                resultados = list(ddgs.text(query_aberta, region="br-pt", max_results=3))
                
            if not resultados:
                return "Nenhum resultado encontrado nas fontes oficiais para validar esta informação."
            
            # Formata os resultados para o LLM ler facilmente
            textos = []
            for r in resultados:
                textos.append(f"TÍTULO: {r.get('title')}\nCONTEÚDO: {r.get('body')}\n---")
            
            return "\n".join(textos)
            
    except Exception as e:
        return f"Erro na busca web: {str(e)}"

# 5. Interface de Usuário
st.title("🛡️ Sistema de Validação e Segurança Digital")
st.markdown("**Verifique a veracidade de notícias, detecte links suspeitos e identifique conteúdo gerado por IA.**")

# Abas de entrada de dados
tab1, tab2 = st.tabs(["📝 Texto ou Link", "🖼️ Print / Imagem"])

input_texto = ""

with tab1:
    input_texto = st.text_area(
        "Cole a notícia, o texto viral ou o link aqui:", 
        height=150,
        placeholder="Ex: 'O presidente declarou hoje que...' ou 'Urgente! Clique para resgatar...'"
    )

with tab2:
    foto = st.file_uploader("Suba o print da notícia ou imagem suspeita:", type=['png', 'jpg', 'jpeg'])
    
    # Limpa o estado se a foto for removida
    if foto is None and 'conteudo_extraido' in st.session_state:
        del st.session_state['conteudo_extraido']

    if foto:
        st.image(foto, width=300)
        
        if st.button("Analisar Imagem com IA"):
            with st.spinner("Lendo e analisando a imagem..."):
                try:
                    img_base64 = base64.b64encode(foto.getvalue()).decode()
                    msg = vision_llm.invoke([
                        {"role": "user", "content": [
                            {"type": "text",
                             "text": """
                             Faça duas coisas:
                             1. Transcreva todo o texto legível desta imagem. Se NÃO houver texto na imagem, escreva exatamente: "[TEXTO EXTRAÍDO]: Nenhum texto na imagem".
                             2. Analise a imagem visualmente: Descreva brevemente a cena. Há sinais de manipulação, uso fora de contexto, ou parece ter sido gerada por IA?
                             
                             Retorne no formato:
                             [TEXTO EXTRAÍDO]: <texto>
                             [ANÁLISE VISUAL]: <análise>
                             """},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                        ]}
                    ])
                    st.session_state['conteudo_extraido'] = msg.content
                    st.success("Leitura da imagem concluída!")
                    
                    with st.expander("Ver resultado da leitura visual"):
                        st.write(msg.content)
                        
                except Exception as e:
                    st.error(f"Erro ao analisar a imagem: {e}")

# 6. Lógica Principal de Análise
# Define o que será analisado (texto digitado ou texto extraído da imagem)
conteudo_final = input_texto.strip() if input_texto.strip() else st.session_state.get('conteudo_extraido', "")

st.divider()

if st.button("🚀 ANALISAR CONFIABILIDADE E SEGURANÇA", use_container_width=True):
    if not conteudo_final:
        st.error("Por favor, insira um texto/link na aba 'Texto' ou analise uma foto na aba 'Imagem'!")
    else:
        with st.spinner("Cruzando dados, pesquisando fontes e detectando padrões..."):
            try:
                # Decide se faz a busca web
                if "Nenhum texto na imagem" in conteudo_final:
                    resultados_web = "Busca web ignorada: A imagem não contém texto para pesquisa em sites de notícias. Baseie-se apenas na análise visual."
                else:
                    # Pega as primeiras palavras para formular a pesquisa
                    query_base = conteudo_final[:100].replace('\n', ' ')
                    query = f"{query_base} noticias g1 uol cnn brasil"
                    resultados_web = buscar_web(query)

                # Prompt Template corrigido (Sem erros de aspas)
                template = """
Você é um Especialista em Segurança Digital, Fact-Checking e Educação Midiática.

CONTEÚDO A SER ANALISADO: 
{conteudo}

RESULTADOS DA BUSCA EM FONTES OFICIAIS: 
{resultados}

Sua tarefa é realizar 5 tipos de análise:
1. Verificação de Notícias: O conteúdo bate com os resultados da busca? Há fontes?
2. Verificação de Links/Golpes: Parece phishing? Pede dados? Promete dinheiro fácil?
3. Conteúdo Viral: Usa linguagem alarmista, apela para a emoção ou exige compartilhamento urgente?
4. Conteúdo Gerado por IA: O texto é artificialmente perfeito, repetitivo ou sem opinião humana?
5. Imagem: (Avalie os dados de [ANÁLISE VISUAL] caso existam. Foi gerada por IA? Há manipulação?)

Regras para PONTUAÇÃO (0 a 100):
- Golpes claros, links de phishing ou fake news perigosas: 0 a 30.
- Imagens puramente de IA se passando por reais ou dados sem fontes claras: 31 a 69.
- Confirmado por fontes oficiais, seguro e sem manipulação: 70 a 100.

Retorne o relatório RIGOROSAMENTE neste formato Markdown:

### 🎯 RESULTADO FINAL
- **PONTUAÇÃO:** [Nota de 0 a 100]
- **CLASSIFICAÇÃO:** [Escolha: Confiável, Duvidoso ou Perigoso]

### 🚨 SISTEMA DE ALERTAS
*(Liste apenas os aplicáveis usando emojis, ex: ⚠️ Link perigoso, ❓ Informação não confirmada. Se estiver tudo ok, escreva "✅ Nenhum alerta de risco")*

### 🔎 ANÁLISE DETALHADA:
- **Fatos e Fontes:** (O que dizem as fontes vs o texto analisado)
- **Segurança e Links:** (Análise de phishing/golpe, se aplicável)
- **Análise Visual / IA:** (Se houver imagem, destaque sinais de manipulação)

### 📝 CONCLUSÃO TÉCNICA:
- (Explique o motivo central da pontuação)

### 💡 APRENDA A IDENTIFICAR:
- (Dica prática para o usuário identificar isso sozinho no futuro)
"""
                # Geração da resposta
                prompt = PromptTemplate.from_template(template)
                chain = prompt | text_llm
                
                analise = chain.invoke({
                    "conteudo": conteudo_final, 
                    "resultados": resultados_web
                })

                st.success("Análise completa!")
                st.markdown(analise.content)
                
                # Debug (Opcional) para ver o que a IA leu na internet
                with st.expander("Ver dados brutos da pesquisa na web"):
                    st.write(resultados_web)

            except Exception as e:
                st.error(f"Ocorreu um erro durante a análise: {e}")
