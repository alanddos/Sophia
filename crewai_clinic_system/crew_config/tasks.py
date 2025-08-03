from crewai import Task
from crewai_tools import FileTools
import os

# Carregar os caminhos das especificações do ambiente
PROJECT_STATUS_PATH = os.getenv("PROJECT_STATUS_PATH")
TECHNOLOGIES_AND_ROADMAP_SPEC_PATH = os.getenv("TECHNOLOGIES_AND_ROADMAP_SPEC_PATH")
SYSTEM_FLOW_SPEC_PATH = os.getenv("SYSTEM_FLOW_SPEC_PATH")
DER_SPEC_PATH = os.getenv("DER_SPEC_PATH")

# Ferramentas para manipulação de arquivos
file_tools_project_status = FileTools(
    file_path=PROJECT_STATUS_PATH,
    description="Permite ler e escrever no arquivo JSON de status do projeto. "
                "Use para atualizar a lista de itens concluídos no projeto e verificar o status atual."
)

file_tools_tech_roadmap = FileTools(
    file_path=TECHNOLOGIES_AND_ROADMAP_SPEC_PATH,
    description="Permite ler o arquivo Markdown que contém as tecnologias propostas e o roteiro de desenvolvimento do projeto."
)

file_tools_system_flow = FileTools(
    file_path=SYSTEM_FLOW_SPEC_PATH,
    description="Permite ler o arquivo Markdown que descreve o fluxo geral do sistema."
)

file_tools_der_spec = FileTools(
    file_path=DER_SPEC_PATH,
    description="Permite ler o arquivo Markdown que contém a especificação do Diagrama Entidade-Relacionamento (DER)."
)

# --- Definição das Tarefas ---

orchestrate_development_plan_task = Task(
    description=(
        "Com base nos requisitos e no status atual do projeto, crie um plano de desenvolvimento detalhado. "
        "Considere o seguinte pedido do usuário: '{user_project_plan}'. "
        "O status atual do projeto é: {completed_tasks_context}. "
        "O plano deve ser pragmático, modular e iterativo, identificando os próximos passos claros e as fases envolvidas, "
        "considerando o que já foi feito. Inclua sub-tarefas específicas para cada fase, se aplicável, "
        "e como elas se encaixam no progresso geral do projeto."
    ),
    expected_output=(
        "Um plano de desenvolvimento detalhado, articulado em etapas e sub-tarefas, "
        "levando em conta o estado atual e o que o usuário solicitou."
    ),
    tools=[file_tools_tech_roadmap, file_tools_system_flow, file_tools_der_spec, file_tools_project_status],
    agent=None,  # Será atribuído na Crew
)

analyze_requirements_der_task = Task(
    description=(
        "Analise cuidadosamente os documentos de fluxo do sistema e o DER. "
        "Identifique todos os requisitos funcionais e não-funcionais, e prepare um resumo claro "
        "que servirá de base para o design da arquitetura. "
        "Garanta que a análise esteja alinhada com as necessidades do projeto e com o que já foi feito: {completed_tasks_context}."
    ),
    expected_output="Um resumo detalhado dos requisitos funcionais e não-funcionais, e uma análise do DER.",
    tools=[file_tools_system_flow, file_tools_der_spec, file_tools_project_status],
    agent=None,
)

design_architecture_db_schema_task = Task(
    description=(
        "Com base nos requisitos analisados e no DER, projete a arquitetura geral do sistema e o esquema do banco de dados. "
        "Inclua a estrutura de microsserviços, tecnologias principais e o design de alto nível do banco de dados (tabelas, relações). "
        "Considere as tecnologias propostas no roteiro e o status atual: {completed_tasks_context}. "
        "Crie também a documentação técnica inicial para a arquitetura e o esquema do banco de dados."
    ),
    expected_output="Documentos de design de arquitetura e esquema de banco de dados, detalhando a estrutura do sistema.",
    tools=[file_tools_tech_roadmap, file_tools_der_spec, file_tools_project_status],
    agent=None,
)

develop_backend_auth_skeleton_task = Task(
    description=(
        "Desenvolva o esqueleto para o microsserviço de autenticação do backend. "
        "Isso inclui a configuração inicial do projeto, modelos de usuário, endpoints de registro/login básicos, "
        "e integração com um sistema de autenticação (ex: JWT). "
        "O contexto atual do projeto e tarefas concluídas é: {completed_tasks_context}. "
        "O código deve ser funcional e seguir as melhores práticas de backend."
    ),
    expected_output="Código Python funcional para o esqueleto do microsserviço de autenticação.",
    agent=None,
)

develop_frontend_login_dashboard_skeleton_task = Task(
    description=(
        "Desenvolva o esqueleto para as interfaces de login e dashboard do frontend. "
        "Isso inclui os componentes UI, rotas básicas, e integração inicial com o backend de autenticação. "
        "O contexto atual do projeto e tarefas concluídas é: {completed_tasks_context}. "
        "O código deve ser funcional e seguir as melhores práticas de frontend (ex: React, Next.js)."
    ),
    expected_output="Código React/Next.js funcional para o esqueleto das interfaces de login e dashboard.",
    agent=None,
)

develop_backend_chat_skeleton_task = Task(
    description=(
        "Desenvolva o esqueleto para o microsserviço de chat do backend. "
        "Isso inclui a configuração inicial, modelos de mensagens e salas de chat, e endpoints básicos para envio/recebimento de mensagens. "
        "O contexto atual do projeto e tarefas concluídas é: {completed_tasks_context}. "
        "O código deve ser funcional e seguir as melhores práticas de backend."
    ),
    expected_output="Código Python funcional para o esqueleto do microsserviço de chat.",
    agent=None,
)

develop_frontend_chat_task = Task(
    description=(
        "Desenvolva a interface de chat no frontend e integre-a com o microsserviço de chat do backend. "
        "Isso inclui a UI para exibir mensagens, enviar novas mensagens, e lidar com a comunicação em tempo real (WebSockets, se aplicável). "
        "O contexto atual do projeto e tarefas concluídas é: {completed_tasks_context}. "
        "O código deve ser funcional e seguir as melhores práticas de frontend."
    ),
    expected_output="Código React/Next.js funcional para a interface de chat.",
    agent=None,
)

create_test_plans_task = Task(
    description=(
        "Crie planos de teste abrangentes para todas as funcionalidades desenvolvidas. "
        "Isso inclui casos de teste para o backend (API, lógica de negócios) e frontend (UI, fluxo do usuário). "
        "O contexto atual do projeto e tarefas concluídas é: {completed_tasks_context}. "
        "Priorize testes de integração e end-to-end."
    ),
    expected_output="Documentos detalhados de planos de teste para as funcionalidades desenvolvidas.",
    agent=None,
)

setup_infra_docker_task = Task(
    description=(
        "Configure a infraestrutura básica usando Docker e Docker Compose para os microsserviços do backend e frontend. "
        "Isso inclui a criação de Dockerfiles para cada serviço e um docker-compose.yml para orquestração. "
        "O contexto atual do projeto e tarefas concluídas é: {completed_tasks_context}. "
        "Garanta que a configuração permita um ambiente de desenvolvimento local fácil e reflita a arquitetura proposta."
    ),
    expected_output="Arquivos Dockerfile e docker-compose.yml funcionais para a configuração da infraestrutura.",
    agent=None,
)

update_project_status_task = Task(
    description=(
        "Analise os resultados do planejamento e desenvolvimento mais recentes. "
        "Atualize o arquivo de status do projeto ({PROJECT_STATUS_PATH}) com os novos itens CONCLUÍDOS. "
        "Use o arquivo de roteiro de desenvolvimento em ({TECHNOLOGIES_AND_ROADMAP_SPEC_PATH}) como referência "
        "para identificar as fases ou sub-tarefas que foram efetivamente concluídas ou avançadas. "
        "O plano gerado foi: {planning_result_context}. "
        "Os resultados de desenvolvimento foram: {development_result_context}. "
        "O status anterior era: {completed_tasks_context}. "
        "**Sua saída DEVE ser uma lista JSON de strings contendo APENAS os nomes EXATOS das tarefas ou fases do roteiro que foram definitivamente concluídas, OU os nomes EXATOS de novos artefatos/documentos gerados. NÃO inclua nada além da lista JSON. Exemplo: ['Fase 1: Descoberta e Design', 'DER Analisado', 'Plano de Arquitetura']**."
    ),
    expected_output=(
        "Uma lista JSON de strings contendo os nomes EXATOS das tarefas ou fases do roteiro que foram "
        "concluídas, ou novos artefatos/documentos gerados. EX: ['Fase 1: Descoberta e Design', 'DER Analisado']"
    ),
    tools=[file_tools_project_status, file_tools_tech_roadmap],
    agent=None,
)