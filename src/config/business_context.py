from typing import Dict, List
import yaml
import os

class BusinessContext:
    def __init__(self, config_path: str = None):
        """Inicializa o contexto de negócio
        
        Args:
            config_path: Caminho para o arquivo de configuração YAML. Se não fornecido,
                        usa o arquivo padrão em config/contexts.yaml
        """
        self.contexts = {}
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 
            'contexts.yaml'
        )
        self.load_contexts()
    
    def load_contexts(self):
        """Carrega os contextos do arquivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.contexts = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Arquivo de configuração não encontrado: {self.config_path}")
            self.contexts = {}
    
    def save_contexts(self):
        """Salva os contextos atuais no arquivo YAML"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.contexts, f, allow_unicode=True, sort_keys=False)
    
    def add_context(self, name: str, description: str, tables: Dict[str, Dict], 
                    relationships: List[str], metrics: Dict[str, str]):
        """Adiciona um novo contexto de negócio
        
        Args:
            name: Nome do contexto (ex: 'Vendas', 'Produtos')
            description: Descrição detalhada do contexto
            tables: Dicionário com informações das tabelas
            relationships: Lista de relacionamentos importantes
            metrics: Dicionário de métricas e suas descrições
        """
        self.contexts[name] = {
            'description': description,
            'tables': tables,
            'relationships': relationships,
            'aggregation_fields': metrics
        }
        self.save_contexts()
    
    def get_context(self, name: str) -> Dict:
        """Retorna um contexto específico"""
        return self.contexts.get(name, {})
    
    def get_all_contexts(self) -> Dict:
        """Retorna todos os contextos cadastrados"""
        return self.contexts
    
    def format_for_prompt(self) -> str:
        """Formata todos os contextos para uso no prompt do LLM"""
        prompt = "CONTEXTO DE NEGÓCIOS:\n\n"
        
        for name, context in self.contexts.items():
            prompt += f"=== {name} ===\n"
            prompt += f"Descrição: {context['description']}\n"
            prompt += "\nTabelas Relevantes:\n"
            for table_name, table_info in context['tables'].items():
                prompt += f"- {table_name}\n"
                prompt += f"  Descrição: {table_info['description']}\n"
                if 'primary_key' in table_info:
                    prompt += f"  Chave Primária: {table_info['primary_key']}\n"
                prompt += "  Colunas:\n"
                for col, desc in table_info['columns'].items():
                    prompt += f"    * {col}: {desc}\n"
            
            prompt += "\nRelacionamentos Importantes:\n"
            for rel in context['relationships']:
                prompt += f"- {rel}\n"
            
            prompt += "\nMétricas Disponíveis:\n"
            for metric_key, metric_info in context['aggregation_fields'].items():
                if isinstance(metric_info, dict):
                    prompt += f"- {metric_info.get('display_name', metric_key)}: {metric_info.get('description', '')}\n"
                else:
                    prompt += f"- {metric_key}: {metric_info}\n"
            prompt += "\n"
        
        return prompt 
    
    def format_metrics_for_display(self, context_name: str) -> List[Dict]:
        """Formata as métricas para exibição na interface
        
        Args:
            context_name: Nome do contexto
            
        Returns:
            Lista de métricas formatadas com display_name, description e exemplos
        """
        context = self.get_context(context_name)
        if not context:
            return []
            
        metrics = []
        for metric_key, metric_info in context.get('aggregation_fields', {}).items():
            if isinstance(metric_info, dict):
                metric_data = {
                    'key': metric_key,
                    'display_name': metric_info.get('display_name', metric_key),
                    'description': metric_info.get('description', ''),
                    'examples': metric_info.get('examples', [])
                }
            else:
                # Se for string, usa como descrição
                metric_data = {
                    'key': metric_key,
                    'display_name': metric_key,
                    'description': metric_info,
                    'examples': []
                }
            metrics.append(metric_data)
            
        return metrics 