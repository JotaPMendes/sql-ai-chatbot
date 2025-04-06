import streamlit as st
import requests
import json
import time
from datetime import datetime
import os
import base64

# Configurações da página
st.set_page_config(
    page_title="SQL AI Chatbot",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/sql-ai-chatbot-public',
        'Report a bug': 'https://github.com/yourusername/sql-ai-chatbot-public/issues',
        'About': 'SQL AI Chatbot - Construído com IA para criar consultas SQL a partir de linguagem natural'
    }
)

# Definir variáveis de sessão
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = None
if 'iterations' not in st.session_state:
    st.session_state.iterations = 0
if 'sql_query' not in st.session_state:
    st.session_state.sql_query = ""
if 'explanation' not in st.session_state:
    st.session_state.explanation = ""
if 'processing_time' not in st.session_state:
    st.session_state.processing_time = 0

# URL base da API
API_URL = os.getenv("API_URL", "http://localhost:8000")

# CSS personalizado para um design moderno
st.markdown("""
<style>
/* Variáveis de cores */
:root {
    --primary-color: #4F8BF9;
    --primary-light: #7AA6F9;
    --secondary-color: #ff4b4b;
    --background-light: #f8f9fa;
    --card-color: #ffffff;
    --text-color: #333333;
    --text-light: #767676;
    --shadow: rgba(0, 0, 0, 0.05);
    --border-radius: 10px;
}

/* Texto e tipografia */
h1, h2, h3 {
    color: var(--text-color);
    font-weight: 600;
}

p {
    color: var(--text-color);
    font-size: 1rem;
}

/* Cards com sombra */
.card {
    background-color: var(--card-color);
    border-radius: var(--border-radius);
    box-shadow: 0 4px 12px var(--shadow);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.1);
}

/* Botões estilizados */
.custom-button {
    background-color: var(--primary-color);
    color: white;
    font-weight: 500;
    padding: 0.5rem 1rem;
    border-radius: 30px;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: center;
    display: inline-block;
    margin: 0.2rem 0;
}

.custom-button:hover {
    background-color: var(--primary-light);
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.custom-button-secondary {
    background-color: transparent;
    color: var(--primary-color);
    border: 1px solid var(--primary-color);
}

.custom-button-secondary:hover {
    background-color: rgba(79, 139, 249, 0.1);
}

/* SQL code display */
.sql-code {
    background-color: #272822;
    color: #f8f8f2;
    padding: 1rem;
    border-radius: var(--border-radius);
    font-family: 'Courier New', monospace;
    overflow-x: auto;
    white-space: pre-wrap;
}

/* Headers */
.header {
    border-bottom: 2px solid var(--primary-light);
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
    color: var(--primary-color);
    font-weight: 600;
}

/* Status indicators */
.status-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 5px;
}

.status-success {
    background-color: #00c853;
}

.status-error {
    background-color: #f44336;
}

.status-warning {
    background-color: #ffab40;
}

/* Animations */
@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

.pulse {
    animation: pulse 2s infinite;
}

/* Progress bar */
.progress-container {
    width: 100%;
    background-color: #e0e0e0;
    border-radius: 5px;
    margin: 1rem 0;
}

.progress-bar {
    height: 8px;
    background-color: var(--primary-color);
    border-radius: 5px;
    transition: width 0.3s ease;
}

/* Responsive design */
@media (max-width: 768px) {
    .card {
        padding: 1rem;
    }
    
    h1 {
        font-size: 1.8rem;
    }
    
    h2 {
        font-size: 1.5rem;
    }
}
</style>
""", unsafe_allow_html=True)

# Função para consultar a API
def query_api(question):
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={"question": question, "conversation_id": st.session_state.conversation_id}
        )
        if response.status_code == 200:
            result = response.json()
            st.session_state.conversation_id = result.get("conversation_id")
            st.session_state.iterations = result.get("iteration", 1)
            st.session_state.sql_query = result.get("sql_query", "")
            st.session_state.explanation = result.get("explanation", "")
            st.session_state.processing_time = result.get("processing_time", 0)
            return result
        else:
            st.error(f"Erro ao consultar API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

# Função para refinar a consulta
def refine_query(feedback):
    try:
        if not st.session_state.conversation_id:
            st.warning("Você precisa gerar uma consulta primeiro antes de refiná-la.")
            return None
            
        response = requests.post(
            f"{API_URL}/refine",
            json={"feedback": feedback, "conversation_id": st.session_state.conversation_id}
        )
        if response.status_code == 200:
            result = response.json()
            st.session_state.iterations = result.get("iteration", st.session_state.iterations + 1)
            st.session_state.sql_query = result.get("sql_query", "")
            st.session_state.explanation = result.get("explanation", "")
            st.session_state.processing_time = result.get("processing_time", 0)
            return result
        else:
            st.error(f"Erro ao refinar consulta: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

# Função para copiar texto para a área de transferência
def copy_to_clipboard(text):
    b64 = base64.b64encode(text.encode()).decode()
    html = f"""
        <div>
            <textarea id="text-to-copy" style="opacity:0;height:0;width:0">{text}</textarea>
            <script>
                var copyText = document.getElementById("text-to-copy");
                copyText.select();
                document.execCommand("copy");
            </script>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    st.success("Copiado com sucesso!")

# Função para exportar para arquivo .sql
def export_to_sql(query):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"query_{timestamp}.sql"
    try:
        with open(filename, "w") as f:
            f.write(query)
        st.success(f"Consulta exportada para {filename}")
    except Exception as e:
        st.error(f"Erro ao exportar arquivo: {str(e)}")

# Função para mostrar os resultados
def show_results():
    if st.session_state.sql_query:
        st.markdown(f"<div class='header'><h3>Consulta gerada (iteração {st.session_state.iterations})</h3></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<p class='header'>Explicação da consulta</p>", unsafe_allow_html=True)
            
            with st.expander("Ver explicação detalhada", expanded=True):
                st.markdown(f"{st.session_state.explanation}")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<p class='header'>Consulta SQL</p>", unsafe_allow_html=True)
            
            # Mostrar a query SQL como código
            st.code(st.session_state.sql_query, language="sql")
            
            # Botões para copiar e exportar
            col_copy, col_export = st.columns(2)
            with col_copy:
                if st.button("📋 Copiar SQL", key="copy_sql"):
                    copy_to_clipboard(st.session_state.sql_query)
            
            with col_export:
                if st.button("💾 Exportar SQL", key="export_sql"):
                    export_to_sql(st.session_state.sql_query)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Seção para refinar a consulta
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<p class='header'>Refinar a consulta</p>", unsafe_allow_html=True)
        st.markdown("""
        Descreva o que você deseja ajustar na consulta. Por exemplo:
        - Adicionar um filtro por data específica
        - Agrupar por outra coluna
        - Incluir outra métrica no cálculo
        """)
        
        feedback = st.text_area("O que deseja mudar na consulta?", height=100, max_chars=500)
        if st.button("🔄 Refinar consulta"):
            if feedback:
                with st.spinner("Refinando a consulta..."):
                    result = refine_query(feedback)
                    if result:
                        st.success("Consulta refinada com sucesso!")
                    else:
                        st.error("Não foi possível refinar a consulta.")
            else:
                st.warning("Por favor, informe o que deseja mudar na consulta.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Mostra o tempo de processamento
        if st.session_state.processing_time > 0:
            st.info(f"⏱️ Tempo de processamento: {st.session_state.processing_time} segundos")

# Função principal
def main():
    # Título e descrição
    st.markdown("<h1 class='header'>SQL AI Chatbot</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div class='card'>
    <p>Transforme suas perguntas em linguagem natural em consultas SQL precisas, instantaneamente.</p>
    <p>Basta descrever o que você deseja analisar, e o assistente gerará a consulta SQL correspondente.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Entrada da pergunta
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<p class='header'>O que você deseja analisar?</p>", unsafe_allow_html=True)
    
    question = st.text_area(
        "Digite sua pergunta em linguagem natural",
        placeholder="Exemplo: Qual o total de vendas por região no último mês?",
        height=100,
        max_chars=500
    )
    
    generate = st.button("🚀 Gerar consulta SQL", use_container_width=True)
    
    # Indicador de status para iterações
    if st.session_state.iterations > 0:
        iterations = st.session_state.iterations
        st.markdown(
            f"""
            <div class='progress-container'>
                <div class='progress-bar' style='width: {min(iterations * 33, 100)}%;'></div>
            </div>
            <p style='text-align: center; font-size: 0.8rem;'>
                {iterations}/3 iterações utilizadas
            </p>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Se o botão for clicado, gerar a consulta
    if generate and question:
        with st.spinner("Gerando consulta SQL..."):
            st.session_state.conversation_id = None  # Reset para nova conversa
            result = query_api(question)
            if result:
                st.success("Consulta gerada com sucesso!")
    
    # Mostrar os resultados se existirem
    show_results()
    
    # Dicas de uso
    with st.expander("📚 Dicas de uso"):
        st.markdown("""
        ### Como obter os melhores resultados
        
        1. **Seja específico em suas perguntas**
           - Em vez de "Vendas por mês", pergunte "Qual foi o total de vendas por mês nos últimos 3 meses?"
        
        2. **Mencione filtros importantes**
           - Especifique região, período, categoria ou qualquer outro filtro relevante
        
        3. **Esclareça métricas desejadas**
           - "Quero ver o total de vendas, quantidade de pedidos e ticket médio por região"
        
        4. **Use refinamentos para ajustes**
           - Após receber a consulta inicial, use a função de refinamento para ajustes específicos
        
        ### Exemplos de perguntas eficazes
        
        - "Quais os 10 produtos mais vendidos na região Sul no último trimestre?"
        - "Qual o total de faturamento por categoria de produto em 2023, ordenado do maior para o menor?"
        - "Comparativo de vendas mensais entre 2022 e 2023 por região"
        - "Qual a taxa de conversão de clientes por canal de aquisição nos últimos 6 meses?"
        """)

if __name__ == "__main__":
    main() 