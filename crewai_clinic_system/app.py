import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from celery import Celery
from dotenv import load_dotenv
import re
import time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Importa a função que executa o processo CrewAI
from crew_orchestrator import run_crew_process, get_roadmap_phases_from_file

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your_secret_key_here') # Chave secreta para flash messages

# Configuração do Celery
app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Caminhos para arquivos (lidos do .env)
PROJECT_STATUS_PATH = os.getenv("PROJECT_STATUS_PATH")
TECHNOLOGIES_AND_ROADMAP_SPEC_PATH = os.getenv("TECHNOLOGIES_AND_ROADMAP_SPEC_PATH")
SYSTEM_FLOW_SPEC_PATH = os.getenv("SYSTEM_FLOW_SPEC_PATH")
DER_SPEC_PATH = os.getenv("DER_SPEC_PATH")

# Arquivo para armazenar os resultados da última execução da tarefa Celery
LAST_RUN_RESULTS_PATH = "last_run_results.json"

def load_project_status():
    """Carrega o status do projeto do arquivo JSON."""
    try:
        if os.path.exists(PROJECT_STATUS_PATH):
            with open(PROJECT_STATUS_PATH, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
                return status_data.get("completed_items", [])
        else:
            # Se o arquivo não existe, cria um novo com uma lista vazia
            with open(PROJECT_STATUS_PATH, 'w', encoding='utf-8') as f:
                json.dump({"completed_items": []}, f, indent=2)
            return []
    except json.JSONDecodeError:
        print(f"Erro: Arquivo '{PROJECT_STATUS_PATH}' está corrompido ou mal formatado. Reiniciando status.")
        with open(PROJECT_STATUS_PATH, 'w', encoding='utf-8') as f:
            json.dump({"completed_items": []}, f, indent=2)
        return []
    except Exception as e:
        print(f"Ocorreu um erro ao carregar o status do projeto: {e}")
        return []

def save_project_status(completed_items: list):
    """Salva o status atualizado do projeto no arquivo JSON."""
    try:
        unique_and_sorted_items = sorted(list(set(completed_items)))
        with open(PROJECT_STATUS_PATH, 'w', encoding='utf-8') as f:
            json.dump({"completed_items": unique_and_sorted_items}, f, indent=2)
        print(f"Status do projeto atualizado em '{PROJECT_STATUS_PATH}'.")
    except Exception as e:
        print(f"Erro ao salvar o status atualizado do projeto: {e}")

def load_last_run_results():
    """Carrega os resultados da última execução da tarefa CrewAI do arquivo."""
    try:
        if os.path.exists(LAST_RUN_RESULTS_PATH):
            with open(LAST_RUN_RESULTS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except json.JSONDecodeError:
        print(f"Erro: Arquivo '{LAST_RUN_RESULTS_PATH}' está corrompido ou mal formatado.")
        return None
    except Exception as e:
        print(f"Ocorreu um erro ao carregar os resultados da última execução: {e}")
        return None

def save_last_run_results(results: dict):
    """Salva os resultados da última execução da tarefa CrewAI em um arquivo."""
    try:
        with open(LAST_RUN_RESULTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"Resultados da última execução salvos em '{LAST_RUN_RESULTS_PATH}'.")
    except Exception as e:
        print(f"Erro ao salvar os resultados da última execução: {e}")


@celery.task
def run_crew_task(user_input: str, current_completed_tasks: list):
    """
    Tarefa Celery para executar o processo da CrewAI em segundo plano.
    Salva os resultados em um arquivo após a conclusão.
    """
    app.app_context().push() # Necessário para acessar configurações de app dentro da tarefa Celery
    
    print(f"Iniciando tarefa CrewAI com input: {user_input}")
    
    results = run_crew_process(user_input, current_completed_tasks)
    
    # Atualiza o status do projeto principal
    if results.get("newly_completed_items"):
        updated_completed_tasks = list(set(current_completed_tasks + results["newly_completed_items"]))
        save_project_status(updated_completed_tasks)
        results["current_completed_tasks_after_run"] = updated_completed_tasks # Adiciona para o log
    else:
        results["current_completed_tasks_after_run"] = current_completed_tasks


    save_last_run_results(results) # Salva o resultado completo da execução

    print(f"Tarefa CrewAI concluída. Resultados salvos.")
    return results


@app.route('/', methods=['GET', 'POST'])
def index():
    completed_tasks = load_project_status()
    error_roadmap, roadmap_phases = get_roadmap_phases_from_file()
    
    # Carrega os resultados da última execução do arquivo
    last_run_results = load_last_run_results()
    planning_output = last_run_results.get("planning_result") if last_run_results else None
    development_output = last_run_results.get("development_result") if last_run_results else None
    error_message = last_run_results.get("error") if last_run_results else None

    # Se houver erro ao carregar roadmap, sobrescreve o erro da última execução
    if error_roadmap:
        error_message = error_roadmap.get("error")

    if request.method == 'POST':
        user_input = request.form['user_input']
        
        # Dispara a tarefa Celery em vez de executar diretamente
        # Passa uma cópia das tarefas completas para evitar problemas de referência
        task = run_crew_task.delay(user_input, list(completed_tasks))
        
        flash(f"Processo CrewAI iniciado em segundo plano (Task ID: {task.id}). "
              f"Os resultados aparecerão aqui assim que a tarefa for concluída (pode levar alguns minutos).", 'info')
        
        # Redireciona para evitar reenvio de formulário e para limpar a mensagem flash
        return redirect(url_for('index'))

    return render_template(
        'index.html',
        roadmap_phases=roadmap_phases,
        completed_tasks=completed_tasks,
        planning_output=planning_output,
        development_output=development_output,
        error_message=error_message,
        # Adiciona uma variável para indicar se uma tarefa está em andamento (opcional, requer mais lógica para verificar status em tempo real)
        # current_task_id=request.args.get('task_id') # Se você quiser passar o ID da tarefa na URL para monitoramento
    )


if __name__ == '__main__':
    # Cria as pastas e arquivos de especificação de exemplo se não existirem
    # (Para facilitar o primeiro uso, mas o usuário deve preenchê-los)
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    if not os.path.exists('project_spec'):
        os.makedirs('project_spec')

    if not os.path.exists(SYSTEM_FLOW_SPEC_PATH):
        with open(SYSTEM_FLOW_SPEC_PATH, 'w', encoding='utf-8') as f:
            f.write("# Fluxo do Sistema\n\n- Login de Usuários\n- Agendamento de Consultas\n- Chat com Pacientes")
    if not os.path.exists(DER_SPEC_PATH):
        with open(DER_SPEC_PATH, 'w', encoding='utf-8') as f:
            f.write("# Diagrama Entidade-Relacionamento\n\nUSUARIO { id PK, nome, email } \nCONSULTA { id PK, usuario_id FK, data, hora }")
    if not os.path.exists(TECHNOLOGIES_AND_ROADMAP_SPEC_PATH):
        with open(TECHNOLOGIES_AND_ROADMAP_SPEC_PATH, 'w', encoding='utf-8') as f:
            f.write("# Tecnologias e Roteiro de Desenvolvimento\n\n## Fase 1: Descoberta e Design\n## Fase 2: Configuração e Bootstrap\n## Fase 3: Desenvolvimento Iterativo por Módulos/Funcionalidades\n## Fase 4: Testes Abrangentes e Qualidade\n## Fase 5: Implantação e Operação")
    
    # Se o arquivo de status não existir, cria um vazio
    if not os.path.exists(PROJECT_STATUS_PATH):
        with open(PROJECT_STATUS_PATH, 'w', encoding='utf-8') as f:
            json.dump({"completed_items": []}, f, indent=2)

    app.run(debug=True)