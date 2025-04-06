from langchain.prompts import PromptTemplate
from langchain_deepseek import ChatDeepSeek
from src.config.business_context import BusinessContext
from typing import Dict, List
import re
import json
import os
from datetime import datetime
import difflib

class SQLQueryAgent:
    def __init__(self, api_key: str, model: str = "deepseek-chat", temperature: float = 0):
        """
        Inicializa o agente de consulta SQL.
        
        Args:
            api_key: Chave API do provedor do modelo
            model: Nome do modelo a ser usado
            temperature: Parâmetro de aleatoriedade para geração (0-1)
        """
        self.llm = ChatDeepSeek(
            model=model,
            api_key=api_key,
            temperature=temperature
        )
        self.business_context = BusinessContext()
        self.conversation_history = {}
        
        # Inicializa a memória de aprendizado
        self.learning_memory_file = "learning_memory.json"
        self.learning_memory = self._load_learning_memory()
        
        # Template para o classificador com memória de aprendizado
        self.classifier_prompt = PromptTemplate(
            template="""
Você é um especialista em análise de dados que entende profundamente o contexto de negócios e SQL.

Sua tarefa é analisar a pergunta do usuário e identificar:
1. O domínio principal da pergunta (vendas, produtos, usuários)
2. As métricas necessárias para responder à pergunta
3. Os filtros que devem ser aplicados
4. Os agrupamentos necessários

Pergunta do usuário: {input}

Padrões similares encontrados na memória de aprendizado:
{similar_patterns}

Responda APENAS no formato JSON abaixo:
```json
{{
  "domain": "vendas|produtos|usuarios",
  "metrics": ["faturamento_total", "quantidade_pedidos", "ticket_medio"],
  "filters": [
    {{ "column": "column_name", "operator": "=|>|<|like", "value": "value" }}
  ],
  "groupby": ["column1", "column2"],
  "timeframe": {{ "column": "CREATED_AT", "period": "day|week|month", "range": "last_7_days|last_30_days|custom", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }},
  "order_by": [{{ "column": "column_name", "direction": "asc|desc" }}]
}}
```

Observações:
- Se algum campo não for aplicável, use null ou um array vazio []
- Para o domain, identifique entre: vendas (pedidos, faturamento), produtos (catálogo, estoque), usuarios (clientes, assinaturas)
- Para timeframe, infira o período baseado na pergunta (último mês, últimos 7 dias, etc.)
- Inclua sempre 'país/região' como filtro padrão quando relevante
- Use os padrões similares encontrados na memória como referência quando apropriado

Apenas forneça o JSON, SEM comentários adicionais."""
            ,input_variables=["input", "similar_patterns"]
        )