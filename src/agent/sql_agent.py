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
        
        # Templates para especialistas de domínio (geram SQL parcial)
        self.sales_expert_prompt = PromptTemplate(
            template="""
Você é um especialista em análise de vendas e SQL.

{business_context}

REGRAS IMPORTANTES:
1. Use apenas as tabelas e colunas fornecidas no contexto acima
2. Siga os relacionamentos definidos no contexto
3. Utilize as métricas conforme definidas no contexto

Pergunta do usuário: {input}
Metadados da classificação: {metadata}

Sua tarefa é gerar uma query SQL bem estruturada que:
1. Use CTEs para organizar a lógica
2. Aplique os joins corretos conforme relacionamentos
3. Calcule as métricas conforme definições do contexto
4. Considere os filtros de negócio necessários

Exemplo de saída:
```sql
with pedidos_base as (
  select
    o.CREATED_AT::DATE as data
    , o.ORDER_ID
    , o.TOTAL_PRICE
    , o.REGION
    , o.IS_ONLINE
  from SCHEMA.DATABASE.ORDERS o
  where 1=1
    and o.REGION = 'LATAM'
)

select
  data
  , sum(TOTAL_PRICE) as faturamento
from pedidos_base
group by all
```

Forneça apenas o código SQL, sem explicações ou comentários adicionais."""
            ,input_variables=["input", "metadata", "business_context"]
        )
        
        self.products_expert_prompt = PromptTemplate(
            template="""
Você é um especialista em análise de produtos e estoque e SQL.

{business_context}

REGRAS IMPORTANTES:
1. Use apenas as tabelas e colunas fornecidas no contexto acima
2. Siga os relacionamentos definidos no contexto
3. Considere as regras específicas de cada tipo de produto
4. Utilize os joins corretos para produtos e inventário

Pergunta do usuário: {input}
Metadados da classificação: {metadata}

Sua tarefa é gerar uma query SQL bem estruturada que:
1. Use CTEs para organizar a lógica
2. Aplique os joins corretos conforme relacionamentos
3. Considere os filtros específicos do catálogo
4. Mantenha a consistência dos dados entre warehouses

Exemplo de saída:
```sql
with produtos_base as (
  select
    p.PRODUCT_NAME
    , p.PRODUCT_ID
    , i.WAREHOUSE_ID
    , i.IS_AVAILABLE
    , p.SUPPLIER_ID
  from SCHEMA.DATABASE.PRODUCTS p
  join SCHEMA.DATABASE.INVENTORY i on p.PRODUCT_ID = i.PRODUCT_ID
  where 1=1
    and p.IS_ACTIVE = true
)

select
  PRODUCT_NAME
  , PRODUCT_ID
  , WAREHOUSE_ID
from produtos_base
```

Forneça apenas o código SQL, sem explicações ou comentários adicionais."""
            ,input_variables=["input", "metadata", "business_context"]
        )
        
        # Template para consolidador (constrói a query final)
        self.consolidator_prompt = PromptTemplate(
            template="""
Você é um especialista em SQL que constrói queries bem formatadas, organizadas e eficientes.

Fragmento SQL gerado por especialista: {expert_sql}

Metadados da classificação: {metadata}

Sua tarefa é construir uma query SQL completa, bem formatada e organizada. Siga estas diretrizes:

1. ESTRUTURA E ORGANIZAÇÃO:
   - Use CTEs (WITH) para quebrar lógicas complexas em partes menores
   - Organize cálculos intermediários em CTEs separadas
   - Para comparações temporais, use CTEs diferentes para cada período
   - Mantenha cada CTE focada em uma única responsabilidade

2. FORMATAÇÃO:
   - Escreva preferencialmente as cláusulas em letras minúsculas
   - Coloque a vírgula antes de cada coluna em uma nova linha
   - Para análises temporais, use CREATED_AT como primeira coluna
   - Para agregar, utilize group by all tudo na mesma linha
   - Indente adequadamente as cláusulas
   - Sempre utilize 1=1 no where

3. REGRAS DE NEGÓCIO:
   - Sempre filtre por região/país quando relevante
   - Para pesquisas por nome, use ilike com % ou ilike any
   - Para case when: 'case' em linha única, 'when' em outra linha, 'end as' em outra
   - Prefira funções nativas do banco quando possível

4. EXPLICAÇÃO:
   Antes da query, forneça:
   - Sumário do que foi pedido
   - Explicação da estratégia usada na query
   - Descrição das CTEs (se houver)
   - Principais métricas calculadas

Forneça primeiro a explicação completa e depois a query SQL, separadas por uma linha em branco."""
            ,input_variables=["expert_sql", "metadata"]
        )
        
        # Template para explicação da query
        self.explanation_template = """
SUMÁRIO DO PEDIDO:
{summary}

ESTRATÉGIA DA QUERY:
{strategy}

ESTRUTURA:
{structure}

PRINCIPAIS MÉTRICAS:
{metrics}
"""
        
        # Template personalizado incluindo contexto de negócios
        self.custom_prompt = PromptTemplate(
            template="""
Você é um especialista em análise de dados que entende profundamente o contexto de negócios e SQL.

{business_context}

Pergunta do usuário: {input}

Siga estas instruções rigorosamente:

1. ANÁLISE DO CONTEXTO:
   - Identifique as métricas necessárias
   - Verifique os filtros requeridos
   - Confirme os campos de agrupamento
   - Sempre que a ideia for complexa, separe a cadeia lógica em CTEs e tente retornar o resultado/comparativo em uma query
   - Só utilize as colunas que forem necessárias para a query, não adicione colunas que não serão utilizadas

2. CONSTRUÇÃO DA QUERY:
   - Use apenas as tabelas e colunas fornecidas no contexto de negócios;
   - Inclua aliases claros para todas as tabelas;
   - Formate datas usando funções adequadas como DATE_TRUNC quando necessário;
   - Escreva preferencialmente as claúsulas em letras minúsculas;
   - Quando separando as colunas no SELECT, coloque a vírgula antes de cada coluna, sendo que cada coluna deve estar em uma linha diferente;
   - Para análises temporais, use sempre CREATED_AT e o deixe sempre como primeira coluna;
   - Para agregar, utilize group by all tudo na mesma linha;
   - Para toda a claúsula, sempre em uma linha única;
   - Ordene os resultados de forma relevante e tudo na mesma linha;
   - Indente as claúsulas de forma adequada;
   - Sempre utilize 1=1 no where;
   - Sempre que for pesquisar por um nome utilize o ilike com % (ex: ilike '%nome%') ou ilike any com % (ex: ilike any ('%nome_1%', '%nome_2%'));
   - Sempre que tiver 'case when' o 'case' fica em uma linha única e o 'when' em outra linha, 'end as' em outra linha;
   - Se necessário, faça suposições plausíveis para os dados que não tenha total certeza.

3. VALIDAÇÃO:
   - Verifique se todos os campos existem nas tabelas
   - Confirme se os joins são necessários
   - Certifique-se de que os filtros estão corretos
   - Valide se as agregações fazem sentido

Primeiro, forneça uma breve explicação do que a query faz.
Em seguida, forneça a query SQL completa e bem formatada.

IMPORTANTE: A query deve começar com a palavra 'SELECT' em uma nova linha."""
            ,input_variables=["business_context", "input"]
        )
        
        # Template para refinamento de query
        self.refinement_prompt = PromptTemplate(
            template="""
Você é um especialista em análise de dados que entende profundamente o contexto de negócios e SQL.

{business_context}

Histórico da conversa:
Pergunta original: {original_question}
Query SQL gerada anteriormente:
```sql
{previous_query}
```

Feedback/solicitação de refinamento do usuário: {feedback}

Sua tarefa é refinar a query SQL anterior com base no feedback do usuário. 
Mantenha o estilo e as boas práticas da query anterior, mas incorpore as melhorias solicitadas.

Siga estas instruções rigorosamente:
1. Analise cuidadosamente o feedback do usuário
2. Identifique os pontos específicos que precisam ser melhorados
3. Mantenha todas as boas práticas de SQL utilizadas anteriormente
4. Forneça uma explicação clara das mudanças feitas

Primeiro, forneça uma breve explicação das mudanças realizadas.
Em seguida, forneça a query SQL refinada completa e bem formatada.

IMPORTANTE: A query deve começar com a palavra 'SELECT' em uma nova linha."""
            ,input_variables=["business_context", "original_question", "previous_query", "feedback"]
        )
    
    def _load_learning_memory(self) -> Dict:
        """Carrega a memória de aprendizado do arquivo JSON"""
        try:
            if os.path.exists(self.learning_memory_file):
                with open(self.learning_memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"patterns": []}
        except Exception as e:
            print(f"Erro ao carregar memória de aprendizado: {str(e)}")
            return {"patterns": []}
    
    def _save_learning_memory(self):
        """Salva a memória de aprendizado no arquivo JSON"""
        try:
            with open(self.learning_memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.learning_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar memória de aprendizado: {str(e)}")
    
    def _find_similar_patterns(self, question: str) -> List[Dict]:
        """Encontra padrões similares na memória de aprendizado"""
        similar_patterns = []
        
        # Extrai palavras-chave da pergunta
        keywords = set(word.lower() for word in question.split())
        
        for pattern in self.learning_memory["patterns"]:
            pattern_keywords = set(word.lower() for word in pattern["question"].split())
            # Calcula similaridade usando difflib
            similarity = difflib.SequenceMatcher(
                None, 
                question.lower(), 
                pattern["question"].lower()
            ).ratio()
            
            # Verifica sobreposição de palavras-chave
            keyword_overlap = len(keywords.intersection(pattern_keywords)) / len(keywords)
            
            # Se houver boa similaridade ou sobreposição de palavras-chave
            if similarity > 0.6 or keyword_overlap > 0.7:
                similar_patterns.append(pattern)
        
        # Retorna até 3 padrões mais relevantes
        return similar_patterns[:3]
    
    def _add_to_learning_memory(self, question: str, metadata: Dict, sql_query: str, success: bool = True):
        """Adiciona um novo padrão à memória de aprendizado"""
        try:
            # Cria um novo padrão
            pattern = {
                "question": question,
                "domain": metadata.get("domain"),
                "metrics": metadata.get("metrics", []),
                "filters": metadata.get("filters", []),
                "sql_pattern": sql_query,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
            
            # Adiciona à memória
            self.learning_memory["patterns"].append(pattern)
            
            # Mantém apenas os últimos 1000 padrões
            if len(self.learning_memory["patterns"]) > 1000:
                self.learning_memory["patterns"] = self.learning_memory["patterns"][-1000:]
            
            # Salva a memória atualizada
            self._save_learning_memory()
            
        except Exception as e:
            print(f"Erro ao adicionar à memória de aprendizado: {str(e)}")
    
    def classify_query(self, question: str) -> Dict:
        """Classifica a pergunta para identificar domínio, métricas e filtros necessários"""
        try:
            # Encontra padrões similares
            similar_patterns = self._find_similar_patterns(question)
            
            # Formata os padrões para o prompt
            patterns_text = "Nenhum padrão similar encontrado."
            if similar_patterns:
                patterns_text = "\n".join([
                    f"- Pergunta: {p['question']}\n  Domínio: {p['domain']}\n  Métricas: {', '.join(p['metrics'])}"
                    for p in similar_patterns
                ])
            
            # Chama o modelo para classificação
            result = self.llm.invoke(
                self.classifier_prompt.format(
                    input=question,
                    similar_patterns=patterns_text
                )
            )
            
            # Processa o resultado como antes
            result_text = str(result.content)
            if "```json" in result_text:
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            elif "```" in result_text:
                result_text = result_text.replace("```", "").strip()
            
            metadata = json.loads(result_text)
            
            # Garante filtro de região/país se necessário
            has_region_filter = False
            if metadata.get("filters"):
                for filter_item in metadata["filters"]:
                    if filter_item.get("column", "").upper() in ["COUNTRY", "REGION"]:
                        has_region_filter = True
                        break
            
            # Aplicamos um filtro padrão de região apenas se for domínio de vendas ou produtos
            # e não houver já um filtro de região
            domain = metadata.get("domain", "").lower()
            if not has_region_filter and domain in ["vendas", "produtos"]:
                if not "filters" in metadata or not metadata["filters"]:
                    metadata["filters"] = []
                metadata["filters"].append({
                    "column": "REGION", 
                    "operator": "=", 
                    "value": "LATAM"
                })
            
            return metadata
            
        except Exception as e:
            print(f"Erro na classificação: {str(e)}")
            return {
                "domain": "vendas",
                "metrics": [],
                "filters": [],
                "groupby": [],
                "timeframe": None,
                "error": str(e)
            }
    
    def generate_expert_sql(self, question: str, metadata: Dict) -> str:
        """Gera o fragmento SQL baseado no domínio usando o especialista apropriado"""
        try:
            domain = metadata.get("domain", "vendas").lower()
            
            # Obtém o contexto de negócio formatado
            business_context = self.business_context.format_for_prompt()
            
            # Seleciona o template apropriado
            if domain == "produtos":
                expert_prompt = self.products_expert_prompt
            else:  # default para vendas
                expert_prompt = self.sales_expert_prompt
            
            # Invoca o LLM com o prompt do especialista
            result = self.llm.invoke(
                expert_prompt.format(
                    input=question,
                    metadata=json.dumps(metadata, ensure_ascii=False),
                    business_context=business_context
                )
            )
            
            # Extrai o SQL da resposta
            result_text = str(result.content)
            
            # Remove backticks
            if "```sql" in result_text:
                result_text = result_text.replace("```sql", "").replace("```", "").strip()
            elif "```" in result_text:
                result_text = result_text.replace("```", "").strip()
            
            return result_text
            
        except Exception as e:
            print(f"Erro ao gerar SQL especialista: {str(e)}")
            return "SELECT * FROM SCHEMA.DATABASE.ORDERS"
    
    def consolidate_sql(self, expert_sql: str, metadata: Dict) -> Dict:
        """Consolida o fragmento SQL do especialista em uma query completa"""
        try:
            # Invoca o LLM para consolidar a query
            result = self.llm.invoke(
                self.consolidator_prompt.format(
                    expert_sql=expert_sql,
                    metadata=json.dumps(metadata, ensure_ascii=False)
                )
            )
            
            # Extrai o SQL
            result_text = str(result.content)
            
            # Remove marcadores de código
            if "```sql" in result_text:
                result_text = result_text.replace("```sql", "").replace("```", "").strip()
            elif "```" in result_text:
                result_text = result_text.replace("```", "").strip()
            
            # Gera explicação automática
            explanation = self._generate_explanation(expert_sql, metadata)
            
            return {
                "sql_query": result_text,
                "explanation": explanation
            }
            
        except Exception as e:
            # Fallback para explicação de erro
            return {
                "sql_query": expert_sql,
                "explanation": f"Query consolidada diretamente do especialista. (Erro: {str(e)})"
            }
    
    def _generate_explanation(self, expert_sql: str, metadata: Dict) -> str:
        """Gera uma explicação detalhada para a query baseada nos metadados"""
        domain = metadata.get("domain", "vendas")
        metrics = metadata.get("metrics", [])
        filters = metadata.get("filters", [])
        groupby = metadata.get("groupby", [])
        
        # Gera sumário do pedido
        summary = f"Análise de {domain} "
        if metrics:
            summary += f"focando em {', '.join(metrics)}"
        if filters:
            filter_desc = [f"{f['column']} {f['operator']} {f['value']}" for f in filters]
            summary += f" com filtros: {', '.join(filter_desc)}"
        if groupby:
            summary += f" agrupado por {', '.join(groupby)}"
            
        # Gera explicação da estratégia
        strategy = []
        if domain == "vendas":
            strategy.append("Utilizando a tabela principal de vendas (ORDERS)")
            if "faturamento_total" in metrics:
                strategy.append("Calculando faturamento através de TOTAL_PRICE")
            if "quantidade_pedidos" in metrics:
                strategy.append("Contando pedidos únicos através de ORDER_ID")
            if "ticket_medio" in metrics:
                strategy.append("Calculando ticket médio (faturamento / número de pedidos)")
        elif domain == "produtos":
            strategy.append("Analisando o catálogo de produtos (PRODUCTS) e inventário (INVENTORY)")
            
        # Retorna explicação formatada
        return self.explanation_template.format(
            summary=summary,
            strategy="\n".join(strategy),
            structure="Query organizada com CTEs para melhor legibilidade e manutenção" if "with" in expert_sql.lower() else "Query direta sem necessidade de CTEs",
            metrics="\n".join(f"- {m}" for m in metrics)
        )
    
    def query(self, question: str, conversation_id: str = None) -> Dict:
        """Gera uma query SQL a partir de uma pergunta em linguagem natural"""
        try:
            if not conversation_id:
                import uuid
                conversation_id = str(uuid.uuid4())
            
            print(f"[AGENT] Classificando pergunta: {question}")
            metadata = self.classify_query(question)
            print(f"[AGENT] Classificação: {metadata}")
            
            expert_sql = self.generate_expert_sql(question, metadata)
            print(f"[AGENT] SQL especialista: {expert_sql}")
            
            result = self.consolidate_sql(expert_sql, metadata)
            sql_query = result["sql_query"]
            explanation = result["explanation"]
            print(f"[AGENT] SQL final: {sql_query}")
            
            # Adiciona à memória de aprendizado
            self._add_to_learning_memory(question, metadata, sql_query, success=True)
            
            self.conversation_history[conversation_id] = {
                "original_question": question,
                "metadata": metadata,
                "iterations": [
                    {
                        "explanation": explanation,
                        "sql_query": sql_query
                    }
                ]
            }
            
            return {
                "status": "success",
                "sql_query": sql_query,
                "explanation": explanation,
                "conversation_id": conversation_id,
                "iteration": 1
            }
            
        except Exception as e:
            print(f"[AGENT] Erro: {str(e)}")
            # Em caso de erro, ainda tenta adicionar à memória para aprender com falhas
            try:
                self._add_to_learning_memory(
                    question, 
                    {"domain": "unknown", "metrics": []}, 
                    "", 
                    success=False
                )
            except:
                pass
                
            # Continua com o fallback como antes
            try:
                business_context = self.business_context.format_for_prompt()
                result = self.llm.invoke(
                    self.custom_prompt.format(
                        input=question,
                        business_context=business_context
                    )
                )
                
                result_text = str(result.content)
                sql_pattern = r'SELECT[\s\S]*'
                sql_match = re.search(sql_pattern, result_text)
                
                if sql_match:
                    sql_query = sql_match.group(0).strip()
                    explanation = result_text[:sql_match.start()].strip()
                else:
                    parts = result_text.split('SELECT')
                    explanation = parts[0].strip()
                    sql_query = 'SELECT' + parts[1].strip() if len(parts) > 1 else result_text
                
                self.conversation_history[conversation_id] = {
                    "original_question": question,
                    "iterations": [
                        {
                            "explanation": explanation,
                            "sql_query": sql_query
                        }
                    ],
                    "fallback_used": True
                }
                
                return {
                    "status": "success",
                    "sql_query": sql_query,
                    "explanation": explanation,
                    "conversation_id": conversation_id,
                    "iteration": 1,
                    "used_fallback": True
                }
                
            except Exception as fallback_error:
                return {"status": "error", "message": f"Erro original: {str(e)}, Erro no fallback: {str(fallback_error)}"}
    
    def refine_query(self, feedback: str, conversation_id: str) -> Dict:
        """Refina uma query SQL com base no feedback do usuário
        
        Args:
            feedback: Feedback ou pedido de refinamento do usuário
            conversation_id: ID da conversa para recuperar histórico
        """
        try:
            # Verifica se a conversa existe
            if conversation_id not in self.conversation_history:
                return {"status": "error", "message": "Conversa não encontrada"}
                
            # Recupera informações da conversa
            conversation = self.conversation_history[conversation_id]
            iterations = conversation["iterations"]
            
            # Limita a 3 iterações (original + 2 refinamentos)
            if len(iterations) >= 3:
                return {"status": "error", "message": "Limite de iterações atingido (máximo 3)"}
            
            # Recupera a última query e a pergunta original
            previous_iteration = iterations[-1]
            original_question = conversation["original_question"]
            previous_query = previous_iteration["sql_query"]
            
            # Se já existe metadata da classificação, usa ela
            metadata = conversation.get("metadata", None)
            
            # Se usou o método de agentes aninhados e tem metadata
            if metadata:
                # Atualiza a metadata com o feedback
                metadata["feedback"] = feedback
                
                # Usa a abordagem de agentes aninhados para refinamento
                # Gera o SQL especialista novamente, mas considerando o feedback
                expert_sql = self.generate_expert_sql(f"{original_question}\n\nConsiderando o feedback: {feedback}", metadata)
                
                # Consolidar com base na versão anterior e no feedback
                result = self.consolidate_sql(expert_sql, metadata)
                sql_query = result["sql_query"]
                explanation = f"Query refinada conforme feedback: {feedback}"
            else:
                # Fallback para o método original
                # Adiciona contexto de negócios ao prompt
                business_context = self.business_context.format_for_prompt()
                
                # Usa o LLM para refinar a query
                result = self.llm.invoke(
                    self.refinement_prompt.format(
                        business_context=business_context,
                        original_question=original_question,
                        previous_query=previous_query,
                        feedback=feedback
                    )
                )
                
                # Converte o resultado para string e divide em explicação e query
                result_text = str(result.content)
                
                # Usa expressão regular para extrair a parte SQL
                sql_pattern = r'SELECT[\s\S]*'
                sql_match = re.search(sql_pattern, result_text)
                
                if sql_match:
                    sql_query = sql_match.group(0).strip()
                    explanation = result_text[:sql_match.start()].strip()
                else:
                    # Fallback para o método anterior
                    parts = result_text.split('SELECT')
                    explanation = parts[0].strip()
                    sql_query = 'SELECT' + parts[1].strip() if len(parts) > 1 else result_text
            
            # Adiciona ao histórico de iterações
            iterations.append({
                "feedback": feedback,
                "explanation": explanation,
                "sql_query": sql_query
            })
            
            return {
                "status": "success",
                "sql_query": sql_query,
                "explanation": explanation,
                "conversation_id": conversation_id,
                "iteration": len(iterations)
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def add_business_context(self, name: str, description: str, tables: Dict[str, Dict], 
                           relationships: List[Dict], metrics: Dict[str, Dict]):
        """Adiciona um novo contexto de negócio
        
        Args:
            name: Nome do contexto (ex: "Vendas", "Produtos")
            description: Descrição do contexto
            tables: Dicionário com tabelas e suas definições
            relationships: Lista de relacionamentos entre tabelas
            metrics: Dicionário com métricas suportadas
        """
        self.business_context.add_context(name, description, tables, relationships, metrics) 