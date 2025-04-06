from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List, Any
import os
from src.agent.sql_agent import SQLQueryAgent
import logging
import time
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("sql-ai-chatbot")

app = FastAPI(
    title="SQL AI Chatbot API",
    description="API para geração de consultas SQL baseadas em perguntas em linguagem natural",
    version="1.0.0"
)

# Configurar CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

# Obter a chave API do ambiente ou usar um valor padrão para desenvolvimento
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# Modelos Pydantic
class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class RefinementRequest(BaseModel):
    feedback: str
    conversation_id: str

class TokenTestRequest(BaseModel):
    text: str

# Instanciar o agente SQL
@app.on_event("startup")
async def startup_event():
    if not API_KEY:
        logger.warning("API_KEY não configurada. A API funcionará em modo de demonstração.")
    
    app.state.sql_agent = SQLQueryAgent(api_key=API_KEY)
    logger.info("Agente SQL inicializado com sucesso.")

# Endpoints
@app.get("/")
async def root():
    """Endpoint de verificação para garantir que a API está funcionando"""
    return {"message": "SQL AI Chatbot API está ativa!"}

@app.post("/query")
async def generate_query(request: QueryRequest):
    """Gerar uma consulta SQL a partir de uma pergunta em linguagem natural"""
    start_time = time.time()
    logger.info(f"Processando pergunta: {request.question}")
    
    try:
        # Acesso ao agente inicializado durante o startup
        sql_agent = app.state.sql_agent
        
        # Gerar a query SQL
        result = sql_agent.query(
            question=request.question,
            conversation_id=request.conversation_id
        )
        
        processing_time = round(time.time() - start_time, 2)
        logger.info(f"Query gerada em {processing_time}s")
        
        # Adicionar o tempo de processamento ao resultado
        result["processing_time"] = processing_time
        
        return result
    
    except Exception as e:
        logger.error(f"Erro ao gerar query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar a requisição: {str(e)}"
        )

@app.post("/refine")
async def refine_query(request: RefinementRequest):
    """Refinar uma consulta SQL existente com base no feedback do usuário"""
    start_time = time.time()
    logger.info(f"Refinando consulta com feedback: {request.feedback}")
    
    try:
        # Acesso ao agente inicializado durante o startup
        sql_agent = app.state.sql_agent
        
        # Refinar a query
        result = sql_agent.refine_query(
            feedback=request.feedback,
            conversation_id=request.conversation_id
        )
        
        processing_time = round(time.time() - start_time, 2)
        logger.info(f"Query refinada em {processing_time}s")
        
        # Adicionar o tempo de processamento ao resultado
        result["processing_time"] = processing_time
        
        return result
    
    except Exception as e:
        logger.error(f"Erro ao refinar query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar a requisição: {str(e)}"
        )

@app.post("/token-usage")
async def check_token_usage(request: TokenTestRequest):
    """Verificar o consumo de tokens para um determinado texto"""
    try:
        input_tokens = len(request.text.split())
        estimated_cost = (input_tokens / 1000) * 0.00144 # Atribuindo (0.0007 / 1k tokens de input + 0.0027 / 1k tokens de input (cache miss) + 0.0110 / 1k tokens de output)
        
        return {
            "status": "success",
            "token_count": input_tokens,
            "estimated_input_cost": f"${estimated_cost:.6f}",
            "message": f"Estimativa para {input_tokens} tokens (palavras). Custos reais podem variar."
        }
    except Exception as e:
        logger.error(f"Erro ao calcular uso de tokens: {str(e)}")
        return {
            "status": "error",
            "message": f"Erro ao calcular uso de tokens: {str(e)}"
        }

# Se executado diretamente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 