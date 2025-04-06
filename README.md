# SQL AI Chatbot

O SQL AI Chatbot é uma ferramenta que permite gerar consultas SQL a partir de perguntas em linguagem natural. Esta solução utiliza modelos de linguagem avançados para transformar perguntas como "Qual o total de vendas por região no último mês?" em consultas SQL precisas e bem estruturadas.

## Características principais

- **Interface amigável**: Interface intuitiva em Streamlit para formular perguntas
- **Geração de SQL**: Transformação automática de linguagem natural para SQL
- **Explicações detalhadas**: Cada consulta vem com explicações sobre o que está sendo feito
- **Refinamento interativo**: Possibilidade de ajustar as consultas com feedback adicional
- **Organização por CTEs**: Queries SQL bem estruturadas usando CTEs para melhor legibilidade
- **Formatação consistente**: Código SQL formatado seguindo boas práticas
- **Exportação de queries**: Opção para copiar ou salvar consultas em arquivos .sql

## Estrutura do projeto

```
sql-ai-chatbot/
├── src/
│   ├── agent/             # Lógica do agente de IA para geração de SQL
│   ├── api/               # Endpoints da API FastAPI
│   ├── config/            # Configurações e contexto de negócios
│   └── frontend/          # Interface Streamlit
└── requirements.txt       # Dependências do projeto
```

## Pré-requisitos

- Python 3.9+
- Chave API para um provedor de modelos de linguagem (DeepSeek, OpenAI, etc.)

## Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/yourusername/sql-ai-chatbot.git
   cd sql-ai-chatbot
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Configure a chave API:
   
   Crie um arquivo `.env` na raiz do projeto:
   ```
   LLM_API_KEY=sua_chave_api_aqui
   ```

## Configuração do contexto de negócios

O arquivo `src/config/contexts.yaml` contém a definição das tabelas, relacionamentos e métricas do seu domínio de negócios. Este arquivo deve ser editado para refletir a estrutura específica do seu banco de dados.

Exemplo de configuração:
```yaml
vendas:
  description: "Contexto de vendas e faturamento"
  tables:
    ORDERS:
      description: "Tabela de pedidos"
      columns:
        ORDER_ID: "ID único do pedido"
        CREATED_AT: "Data e hora de criação do pedido"
        TOTAL_PRICE: "Valor total do pedido"
        REGION: "Região do pedido"
  relationships:
    - table1: "ORDERS"
      table2: "ORDER_ITEMS"
      join_on: "ORDER_ID"
  metrics:
    faturamento_total:
      description: "Soma do TOTAL_PRICE de todos os pedidos"
      formula: "SUM(TOTAL_PRICE)"
```

## Iniciando a aplicação

1. Inicie o backend da API:
   ```
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Em outro terminal, inicie o frontend:
   ```
   streamlit run src/frontend/app.py
   ```

3. Acesse o aplicativo no navegador:
   ```
   http://localhost:8501
   ```

## Como usar

1. Na interface Streamlit, digite uma pergunta em linguagem natural sobre os dados que você quer analisar.
2. Clique em "Gerar consulta SQL".
3. Analise a consulta SQL gerada e sua explicação detalhada.
4. Se necessário, use a seção "Refinar" para ajustar a consulta.
5. Copie ou exporte a consulta SQL para uso em seu banco de dados.

## Monitoramento de token

Para verificar o consumo de tokens, utilize o endpoint:
```
POST http://localhost:8000/token-usage
Content-Type: application/json

{
  "text": "Sua pergunta ou contexto aqui"
}
```

## Exemplos de perguntas eficazes

- "Quais os 10 produtos mais vendidos na região Sul no último trimestre?"
- "Qual o total de faturamento por categoria de produto em 2023, ordenado do maior para o menor?"
- "Comparativo de vendas mensais entre 2022 e 2023 por região"
- "Qual a taxa de conversão de clientes por canal de aquisição nos últimos 6 meses?"

## Personalização

### Adaptando para outros modelos de linguagem

O sistema atualmente usa DeepSeek, mas pode ser adaptado para outros modelos:

1. Modifique a classe `SQLQueryAgent` em `src/agent/sql_agent.py` para usar outro provedor.
2. Atualize as dependências no `requirements.txt`.

### Modificando o contexto de negócios

Para adicionar novos contextos ou alterar o existente:

1. Edite o arquivo `src/config/contexts.yaml`.
2. Reinicie o servidor da API para carregar as mudanças.

## Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes. 