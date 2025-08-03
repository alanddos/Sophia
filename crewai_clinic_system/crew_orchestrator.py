import os
import json
from dotenv import load_dotenv
from crewai import Crew, Process
import re

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Carregar os caminhos das especificações
SYSTEM_FLOW_SPEC_PATH = os.getenv("SYSTEM_FLOW_SPEC_PATH")
DER_SPEC_PATH = os.getenv("DER_SPEC_PATH")
TECHNOLOGIES_AND_ROADMAP_SPEC_PATH = os.getenv("TECHNOLOGIES_AND_ROADMAP_SPEC_PATH")
PROJECT_STATUS_PATH = os.getenv("PROJECT_STATUS_PATH")

# Importar agentes e tarefas
from crew_config.agents import (
    product_owner,
    tech_lead,
    backend_developer,
    frontend_developer,
    qa_engineer,
    devops_engineer
)
from crew_config.tasks import (
    orchestrate_development_plan_task,
    analyze_requirements_der_task,
    design_architecture_db_schema_task,
    develop_backend_auth_skeleton_task,
    develop_frontend_login_dashboard_skeleton_task,
    develop_backend_chat_skeleton_task,
    develop_frontend_chat_task,
    create_test_plans_task,
    setup_infra_docker_task,
    update_project_status_task
)

def get_roadmap_phases_from_file():
    """Lê o arquivo de roteiro e extrai as fases."""
    try:
        if not os.path.exists(TECHNOLOGIES_AND_ROADMAP_SPEC_PATH):
            return {"error": f"Erro: O arquivo de roteiro '{TECHNOLOGIES_AND_ROADMAP_SPEC_PATH}' não foi encontrado."}, []
        with open(TECHNOLOGIES_AND_ROADMAP_SPEC_PATH, 'r', encoding='utf-8') as f:
            roadmap_content = f.read()
        phases = re.findall(r"(Fase \d+: .*?)\n", roadmap_content)
        return None, [phase.strip() for phase in phases]
    except Exception as e:
        return {"error": f"Erro ao ler ou parsear o roteiro: {e}"}, []


def run_crew_process(user_input: str, current_completed_tasks: list):
    """
    Executa o processo CrewAI com base na entrada do usuário e no status atual do projeto.
    Retorna os resultados do planejamento, do desenvolvimento e os itens recém-concluídos.
    """
    
    # --- Etapa 0: Processar Entrada do Usuário e Status ---
    user_project_plan = ""
    tasks_for_dev_crew = []

    # Read roadmap content to get phases
    error_roadmap, phases = get_roadmap_phases_from_file()
    if error_roadmap:
        return error_roadmap # Return the error directly if roadmap loading fails

    selected_indices_list = []
    try:
        selected_indices_list = [int(x.strip()) for x in user_input.split(',') if x.strip().isdigit()]
    except ValueError:
        pass # Not a list of numbers, so it's a specific instruction

    if selected_indices_list:
        user_selected_phases_names = [phases[idx-1] for idx in selected_indices_list if 0 < idx <= len(phases)]
        user_project_plan = f"Desenvolver o sistema, focando nas seguintes fases do roteiro de desenvolvimento: {', '.join(user_selected_phases_names)}."
        
        phase_to_task_mapping = {
            "Fase 1: Descoberta e Design": [analyze_requirements_der_task, design_architecture_db_schema_task],
            "Fase 2: Configuração e Bootstrap": [setup_infra_docker_task],
            "Fase 3: Desenvolvimento Iterativo por Módulos/Funcionalidades": [
                develop_backend_auth_skeleton_task,
                develop_frontend_login_dashboard_skeleton_task,
                develop_backend_chat_skeleton_task,
                develop_frontend_chat_task,
            ],
            "Fase 4: Testes Abrangentes e Qualidade": [create_test_plans_task],
        }

        for selected_phase_name in user_selected_phases_names:
            if selected_phase_name in phase_to_task_mapping:
                for task in phase_to_task_mapping[selected_phase_name]:
                    if task not in tasks_for_dev_crew:
                        tasks_for_dev_crew.append(task)
        
        # Garante que tarefas essenciais para fases de desenvolvimento sejam incluídas
        if any(task in tasks_for_dev_crew for task in [
            develop_backend_auth_skeleton_task, develop_frontend_login_dashboard_skeleton_task,
            develop_backend_chat_skeleton_task, develop_frontend_chat_task
        ]):
            if create_test_plans_task not in tasks_for_dev_crew:
                tasks_for_dev_crew.append(create_test_plans_task)
            if setup_infra_docker_task not in tasks_for_dev_crew:
                tasks_for_dev_crew.append(setup_infra_docker_task)

        if any(phase in user_selected_phases_names for phase in ["Fase 1: Descoberta e Design", "Fase 2: Configuração e Bootstrap", "Fase 3: Desenvolvimento Iterativo por Módulos/Funcionalidades"]):
            if analyze_requirements_der_task not in tasks_for_dev_crew:
                tasks_for_dev_crew.insert(0, analyze_requirements_der_task)
            if design_architecture_db_schema_task not in tasks_for_dev_crew:
                tasks_for_dev_crew.insert(1, design_architecture_db_schema_task)

    else: # User provided a specific instruction
        user_project_plan = user_input
        tasks_for_dev_crew.append(analyze_requirements_der_task)
        tasks_for_dev_crew.append(design_architecture_db_schema_task)


    # --- Etapa 1: Orquestração e Geração do Plano de Desenvolvimento Detalhado ---
    # Formata a descrição da tarefa com o contexto do usuário
    orchestrate_development_plan_task.description = \
        orchestrate_development_plan_task.description.format(
            user_project_plan=user_project_plan,
            completed_tasks_context=str(current_completed_tasks)
        )

    planning_crew = Crew(
        agents=[product_owner],
        tasks=[orchestrate_development_plan_task],
        verbose=True,
        process=Process.sequential,
        manager_llm=product_owner.llm
    )

    planning_result = "N/A"
    try:
        planning_result = planning_crew.kickoff()
    except Exception as e:
        return {"error": f"Erro na etapa de planejamento: {e}", "planning_result": planning_result, "development_result": "N/A", "newly_completed_items": []}

    # --- Etapa 2: Executar as Tarefas de Desenvolvimento ---
    final_development_result = "Nenhuma tarefa de desenvolvimento foi executada."

    # Garante que a tarefa de orquestração não seja passada para a crew de desenvolvimento
    if orchestrate_development_plan_task in tasks_for_dev_crew:
        tasks_for_dev_crew.remove(orchestrate_development_plan_task)

    if tasks_for_dev_crew:
        main_development_crew = Crew(
            agents=[
                product_owner,
                tech_lead,
                backend_developer,
                frontend_developer,
                qa_engineer,
                devops_engineer
            ],
            tasks=tasks_for_dev_crew,
            verbose=True,
            process=Process.sequential,
            manager_llm=product_owner.llm
        )
        try:
            final_development_result = main_development_crew.kickoff()
        except Exception as e:
            return {"error": f"Erro na etapa de desenvolvimento: {e}", "planning_result": planning_result, "development_result": final_development_result, "newly_completed_items": []}

    # --- Etapa 3: Atualizar o Status do Projeto ---
    # Formata a descrição da tarefa de atualização de status
    update_project_status_task.description = \
        update_project_status_task.description.format(
            PROJECT_STATUS_PATH=PROJECT_STATUS_PATH,
            TECHNOLOGIES_AND_ROADMAP_SPEC_PATH=TECHNOLOGIES_AND_ROADMAP_SPEC_PATH,
            planning_result_context=planning_result,
            development_result_context=final_development_result,
            completed_tasks_context=str(current_completed_tasks)
        )

    status_update_crew = Crew(
        agents=[product_owner],
        tasks=[update_project_status_task],
        verbose=True,
        process=Process.sequential,
        manager_llm=product_owner.llm
    )

    status_update_result_str = "[]"
    newly_completed_items = []

    try:
        # Tenta executar a tarefa de atualização de status
        status_update_result_str = status_update_crew.kickoff()
        
        # Tenta parsear a saída JSON
        parsed_result = json.loads(status_update_result_str)
        
        if isinstance(parsed_result, list):
            newly_completed_items = parsed_result
        else:
            raise ValueError("O output do PO para atualização de status não é uma lista JSON válida.")
    
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON na atualização de status: {e}. Output bruto: {status_update_result_str}")
        # Retorna erro, mas não falha todo o processo se desenvolvimento foi bem
        return {
            "error": f"Erro de formato JSON na atualização de status. Tente novamente ou ajuste a instrução. Detalhes: {e}",
            "planning_result": planning_result,
            "development_result": final_development_result,
            "newly_completed_items": []
        }
    except Exception as e:
        print(f"Erro na etapa de atualização de status (não JSON): {e}. Resultado bruto: {status_update_result_str}")
        return {
            "error": f"Erro geral na atualização de status: {e}. Resultado bruto: {status_update_result_str}",
            "planning_result": planning_result,
            "development_result": final_development_result,
            "newly_completed_items": []
        }

    return {
        "planning_result": planning_result,
        "development_result": final_development_result,
        "newly_completed_items": newly_completed_items,
        "error": None
    }