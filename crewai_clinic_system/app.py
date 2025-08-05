import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from celery import Celery
from dotenv import load_dotenv
import re
import time
import crewai_tools

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Importa a função que executa o processo CrewAI
from crew_orchestrator import run_crew_process, get_roadmap_phases_from_file

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your_secret_key_here')

# Configuração do Celery
app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Dicionário de configuração dedicado para o Celery
celery_config = {
    'broker_url': app.config['CELERY_BROKER_URL'],
    'result_backend': app.config['CELERY_RESULT_BACKEND'],
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'America/Sao_Paulo',
    'enable_utc': False,
    'imports': ('crew_orchestrator', ),
}

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(celery_config)

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

# Novo endpoint para verificar o status da tarefa
@app.route('/status/<task_id>')
def task_status(task_id):
    task = run_crew_task.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Aguardando na fila...',
            'result': None
        }
    elif task.state != 'FAILURE':
        # Você pode personalizar as mensagens de status aqui
        response = {
            'state': task.state,
            'status': task.info.get('status', 'Executando...'), # Exemplo de como obter status
            'result': task.info.get('result', None)
        }
    else:
        # Em caso de falha, recupera a informação do erro
        response = {
            'state': task.state,
            'status': str(task.info),
            'result': None
        }
    return jsonify(response)


@app.route('/', methods=['GET', 'POST'])
def index():
    completed_tasks = load_project_status()
    error_roadmap, roadmap_phases = get_roadmap_phases_from_file()
    
    # Correção: Garante que roadmap_phases é um dicionário, mesmo que a função retorne uma lista vazia ou um erro
    if not isinstance(roadmap_phases, dict):
        roadmap_phases = {}
    
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
        
        # Dispara a tarefa Celery e obtém o ID
        task = run_crew_task.delay(user_input, list(completed_tasks))
        
        flash(f"Processo CrewAI iniciado em segundo plano.", 'info')
        
        # Redireciona com o task_id na URL para que o JS possa monitorar
        return redirect(url_for('index', task_id=task.id))

    return render_template(
        'index.html',
        roadmap_phases=roadmap_phases,
        completed_tasks=completed_tasks,
        planning_output=planning_output,
        development_output=development_output,
        error_message=error_message,
    )


if __name__ == '__main__':
    # Cria as pastas e arquivos de especificação de exemplo se não existirem
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