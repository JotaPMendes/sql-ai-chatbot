#!/usr/bin/env python3
"""
Script para iniciar o SQL AI Chatbot (API e frontend).
Executa tanto a API FastAPI quanto o frontend Streamlit em processos separados.
"""

import os
import argparse
import subprocess
import sys
import time
import signal
import atexit
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Processos em execução
processes = []

def cleanup():
    """Encerra todos os processos ao sair"""
    for process in processes:
        try:
            if process.poll() is None: 
                process.terminate()
                print(f"Processo {process.pid} encerrado")
        except Exception as e:
            print(f"Erro ao encerrar processo: {e}")

atexit.register(cleanup)

def signal_handler(sig, frame):
    print("\nRecebi sinal de interrupção. Encerrando processos...")
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_api(host, port, reload=True):
    """Inicia o servidor API FastAPI"""
    print(f"Iniciando API em http://{host}:{port}")
    cmd = [
        "uvicorn", 
        "src.api.main:app", 
        "--host", host, 
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        process = subprocess.Popen(cmd)
        processes.append(process)
        return process
    except Exception as e:
        print(f"Erro ao iniciar API: {e}")
        return None

def start_frontend(port=8501):
    """Inicia o frontend Streamlit"""
    print(f"Iniciando frontend Streamlit em http://localhost:{port}")
    cmd = ["streamlit", "run", "src/frontend/app.py", "--server.port", str(port)]
    
    try:
        process = subprocess.Popen(cmd)
        processes.append(process)
        return process
    except Exception as e:
        print(f"Erro ao iniciar frontend: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Inicia o SQL AI Chatbot")
    parser.add_argument("--api-only", action="store_true", help="Inicia apenas a API")
    parser.add_argument("--frontend-only", action="store_true", help="Inicia apenas o frontend")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Host para API")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Porta para API")
    parser.add_argument("--frontend-port", type=int, default=8501, help="Porta para frontend Streamlit")
    parser.add_argument("--no-reload", action="store_true", help="Desativa reload automático da API")
    
    args = parser.parse_args()
    
    # Verifica se a chave API está configurada
    if not os.getenv("LLM_API_KEY") and not args.frontend_only:
        print("\n⚠️ Atenção: LLM_API_KEY não configurada!")
        print("   A API funcionará em modo demonstração com funcionalidade limitada.")
        print("   Configure sua chave API em um arquivo .env na raiz do projeto.\n")
    
    # Inicia componentes conforme solicitado
    api_process = None
    frontend_process = None
    
    if not args.frontend_only:
        api_process = start_api(args.host, args.port, not args.no_reload)
        time.sleep(2)
    
    if not args.api_only:
        # Verifica se a variável de ambiente API_URL está configurada para o frontend
        if not os.getenv("API_URL"):
            os.environ["API_URL"] = f"http://{args.host}:{args.port}"
            print(f"Configurando API_URL para o frontend: {os.environ['API_URL']}")
        
        frontend_process = start_frontend(args.frontend_port)
    
    # Mantém o script em execução
    try:
        while True:
            time.sleep(1)
            
            # Verifica se os processos ainda estão em execução
            if api_process and api_process.poll() is not None:
                print("API encerrada inesperadamente!")
                if not args.frontend_only:
                    break
            
            if frontend_process and frontend_process.poll() is not None:
                print("Frontend encerrado inesperadamente!")
                if not args.api_only:
                    break
            
            # Se os dois processos encerraram (ou não foram iniciados), sai do loop
            if (api_process is None or api_process.poll() is not None) and \
               (frontend_process is None or frontend_process.poll() is not None):
                break
                
    except KeyboardInterrupt:
        print("\nEncerrando aplicação...")
    finally:
        cleanup()

if __name__ == "__main__":
    main() 