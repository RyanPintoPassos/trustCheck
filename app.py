import streamlit as st
import base64
import os

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from duckduckgo_search import DDGS

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(page_title="TrustCheck", page_icon="🛡️", layout="centered")

vision_llm = ChatGroq(
    model_name="meta-llama/llama-4-scout-17b-16e-instruct",
    groq_api_key=GROQ_API_KEY
)

text_llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY,
    temperature=0.1
)

def buscar(query):
    try:
        with DDGS() as ddgs:
            resultados = ddgs.text(query, max_results=3)
            textos = []

            for r in resultados:
                textos.append(f"{r['title']} - {r['body']}")

            return "\n".join(textos)

    except:
        return "Busca indisponível no momento."

st.title("🛡️ Sistema de Validação e Segurança Digital")
st.markdown("**Verifique a veracidade de notícias, detecte links suspeitos e identifique conteúdo gerado por IA.**")

tab1, tab2 = st.tabs(["📝 Texto ou Link", "🖼️ Print / Imagem"])

input_texto = ""

with tab1:
    input_texto = st.text_area("Cole a notícia, o texto viral ou o link aqui:", height=150,
                               placeholder="Ex: 'Urgente! Clique aqui para resgatar seu prêmio...' ou 'O presidente declarou que...'")

with tab2:
    foto = st.file_uploader("Suba o print da notícia ou imagem suspeita:", type=['png', 'jpg', 'jpeg'])

    if foto is None and 'conteudo_extraido' in st.session_state:
        del st.session_state['conteudo_extraido']

    if foto:
        st.image(foto, width=300)
        if st.button("Analisar Imagem"):
            with st.spinner("Analisando imagem com IA Visual..."):
                try:
                    img_base64 = base64.b64encode(foto.getvalue()).decode()
                    msg = vision_llm.invoke([
                        {"role": "user", "content": [
                            {"type": "text",
                             "text": """
                             Faça duas coisas:
                             1. Transcreva todo o texto legível desta imagem. Se NÃO houver texto na imagem, escreva exatamente: "[TEXTO EXTRAÍDO]: Nenhum texto na imagem".
                             2. Analise a imagem visualmente: Descreva brevemente a cena. Há sinais de manipulação, uso fora de contexto, ou parece ter sido gerada por IA (ex: dedos estranhos, texturas irreais, distorções)?

                             Retorne no formato:
                             [TEXTO EXTRAÍDO]: <texto ou aviso de ausência>
                             [ANÁLISE VISUAL]: <sua análise>
                             """},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                        ]}
                    ])
                    st.session_state['conteudo_extraido'] = msg.content
                    st.success("Análise visual concluída!")
                    with st.expander("Ver resultado da leitura visual"):
                        st.write(msg.content)
                except Exception as e:
                    st.error(f"Erro ao ler a imagem: {e}")

conteudo_final = input_texto.strip() if input_texto.strip() else st.session_state.get('conteudo_extraido', "")

st.divider()
if st.button("🚀 ANALISAR CONFIABILIDADE E SEGURANÇA", use_container_width=True):
    if not conteudo_final:
        st.error("Por favor, insira um texto/link na aba 1 ou analise uma foto na aba 2!")
    else:
        with st.spinner("Cruzando dados, pesquisando fontes e detectando padrões..."):
            try:
                if "Nenhum texto na imagem" in conteudo_final:
                    resultados_web = "Busca web ignorada: A imagem não contém texto para pesquisa em sites de notícias. Baseie-se apenas na análise visual de IA."
                else:
                    query_base = conteudo_final[:100].replace('\n', ' ')
                    query = f"{query_base} site:g1.globo.com OR site:uol.com.br OR site:cnnbrasil.com.br"
                    resultados_web = buscar(query)
                template = """
                Você é um Especialista em Segurança Digital, Fact-Checking e Educação Midiática.

                CONTEÚDO A SER ANALISADO (Pode conter texto, links ou análise de uma imagem): 
                {conteudo}

                RESULTADOS DA BUSCA EM FONTES OFICIAIS: 
                {resultados}

                Sua tarefa é realizar 5 tipos de análise:
                1. Verificação de Notícias: O conteúdo bate com os resultados da busca? Há fontes?
                - Se o conteúdo NÃO possuir link:
                    - NÃO considere automaticamente como falso ou perigoso
                    - Avalie a credibilidade com base na linguagem, coerência e plausibilidade
                    - Verifique se parece uma notícia real (tom neutro, sem exageros)
                2. Verificação de Links/Golpes:
                - Analise:
                    - presença de encurtadores (bit.ly, tinyurl)
                    - domínios incomuns (.xyz, .top, etc.)
                    - pedidos de dados pessoais ou financeiros
                    - promessas exageradas (dinheiro fácil, prêmios)
                3. Conteúdo Viral: Usa linguagem alarmista, apela para a emoção ou exige compartilhamento urgente?
                4. Conteúdo Gerado por IA:
                - Analise:
                    - baixa variação linguística
                    - repetição estrutural
                    - ausência de experiências pessoais
                    - previsibilidade textual
                5. Imagem: (Avalie os dados de [ANÁLISE VISUAL] caso existam. A imagem foi gerada por IA? Há manipulação?)
                - Se houver imagem:
                    - Declare explicitamente: "RECOMENDAÇÃO: Confiar / Não confiar / Duvidoso"
                - Se não houver imagem, não mencione análise visual.

                Regras para PONTUAÇÃO (0 a 100 baseada em Confiabilidade, Consistência e Segurança):
                - Golpes claros, links de phishing ou fake news perigosas: 0 a 30.
                - Imagens puramente de IA se passando por reais ou informações sem fontes claras: 31 a 69.
                - Confirmado por fontes oficiais, seguro e sem manipulação: 70 a 100.
                - A ausência de link NÃO deve reduzir significativamente a pontuação.
                - A penalização só deve ocorrer se houver sinais claros de desinformação.

                Retorne o relatório RIGOROSAMENTE neste formato Markdown:

                ### 🎯 RESULTADO FINAL
                - **PONTUAÇÃO:** [Nota de 0 a 100]
                - **CLASSIFICAÇÃO:** [Escolha APENAS UMA: Confiável, Duvidoso, ou Perigoso]

                ### 🚨 SISTEMA DE ALERTAS
                *(Liste apenas os aplicáveis usando emojis, ex: ⚠️ Link perigoso, ❓ Informação não confirmada, 🧠 Possível imagem gerada por IA, 🎭 Manipulação emocional detectada. Se estiver tudo ok, escreva "✅ Nenhum alerta de risco")*

                ### 🔎 ANÁLISE DETALHADA:
                - **Fatos e Fontes:** (O que dizem as fontes oficiais vs o texto)
                - **Segurança e Links:** (Análise de phishing/golpe, se aplicável)
                - **Análise Visual / IA:** (Se houver descrição de imagem, destaque se há anomalias ou sinais de manipulação)

                ### 📝 CONCLUSÃO TÉCNICA:
                - (Explique o motivo central da pontuação e classificação)

                ### 💡 APRENDA A IDENTIFICAR (Educação ao Usuário):
                - (Dê uma dica prática de como o usuário pode identificar sozinho esse tipo de golpe, fake news ou manipulação de imagem no futuro).
                """

                prompt = PromptTemplate.from_template(template)
                chain = prompt | text_llm

                analise = chain.invoke({"conteudo": conteudo_final, "resultados": resultados_web})

                st.success("Análise completa!")
                st.markdown(analise.content)

            except Exception as e:
                st.error(f"Ocorreu um erro durante a análise: {e}")
