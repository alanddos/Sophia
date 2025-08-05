# 🚀 Sistema de Orquestração de Projetos com CrewAI

Este projeto demonstra um sistema de orquestração de desenvolvimento de software utilizando o framework [CrewAI](https://www.crewai.com/), Flask para a interface web e Celery/Redis para processamento assíncrono de tarefas.

---

## 🌟 Visão Geral do Projeto

O sistema é projetado para:

* **Planejar o Desenvolvimento:** Com base em requisitos e status atual, gera um plano de desenvolvimento detalhado.
* **Analisar Requisitos:** Extrai requisitos de documentos de fluxo e DER.
* **Projetar Arquitetura:** Cria designs de arquitetura e esquemas de banco de dados.
* **Desenvolver Esqueletos de Código:** Gera código inicial para microsserviços de backend (autenticação, chat) e interfaces de frontend.
* **Criar Planos de Teste:** Desenvolve planos de teste abrangentes.
* **Configurar Infraestrutura:** Gera arquivos Dockerfile e Docker Compose para orquestração de serviços.
* **Atualizar Status do Projeto:** Mantém um registro dos itens concluídos.

---

## 🛠️ Pré-requisitos Essenciais

Antes de começar, certifique-se de que os seguintes softwares estão instalados e configurados em seu sistema:

### 🐍 Python (versão 3.11.x ou 3.12.x - **CRÍTICO**)

As versões recentes do `crewai-tools` (e suas dependências) exigem Python 3.10 ou superior. Versões mais antigas ou muito recentes (como 3.13.x) podem causar problemas de compatibilidade. **Recomendamos Python 3.11.x ou 3.12.x.**

* **Como verificar sua versão atual:**
    Abra seu terminal e digite `python --version` ou `py --version`.
* **Se não tiver Python 3.11.x ou 3.12.x:**
    1.  Baixe e instale uma versão estável do Python 3.11.x ou Python 3.12.x do [site oficial do Python](https://www.python.org/downloads/).
    2.  **Durante a instalação no Windows, **MARQUE A CAIXA** "Add Python to PATH" (Adicionar Python ao PATH)**. Isso é crucial!
    3.  **Reinicie seu computador** após a instalação.

### 💾 Servidor Redis

O Redis é usado como *broker* (fila de tarefas) e *backend de resultados* para o Celery. **Ele deve estar rodando antes de iniciar o Celery.**

* **Instalação do Redis (Recomendado para Windows: WSL 2 - Ubuntu):**
    1.  **Habilite WSL 2:**
        * Verifique se a virtualização está ativada na BIOS/UEFI (geralmente "Intel VT-x" ou "AMD-V").
        * No Windows, pesquise "Ativar ou desativar recursos do Windows". Marque **"Plataforma de Máquina Virtual"** e **"Subsistema do Windows para Linux"**. Reinicie se solicitado.
        * Abra o **PowerShell como Administrador** e execute: `wsl --shutdown`.
    2.  **Instale o Redis no WSL (Ubuntu):**
        Abra seu terminal Ubuntu no WSL e execute:
        ```bash
        sudo apt update
        sudo apt install redis-server
        ```
    3.  **Configure o Redis para aceitar conexões externas:**
        Edite o arquivo de configuração do Redis:
        ```bash
        sudo nano /etc/redis/redis.conf
        ```
        Altere/adicione as seguintes linhas:
        ```
        bind 0.0.0.0 ::1
        protected-mode no
        ```
        (Para salvar no nano: `Ctrl + O`, `Enter`, `Ctrl + X`).
    4.  **Reinicie o Redis no WSL:**
        ```bash
        sudo service redis-server restart
        ```
    5.  **Verifique o Status do Redis:**
        ```bash
        ss -ltnp | grep 6379
        ```
        A saída deve mostrar `0.0.0.0:6379`.
    6.  **Configure o Redirecionamento de Porta (Windows <-> WSL):**
        * Obtenha o IP do seu WSL2 no terminal Ubuntu: `hostname -I`. Anote o IP (ex: `172.X.X.X`).
        * Abra o **Prompt de Comando (CMD) como Administrador** no Windows e execute (substitua `<IP_DO_WSL>` pelo IP anotado):
            ```bash
            netsh interface portproxy add v4tov4 listenport=6379 listenaddress=0.0.0.0 connectport=6379 connectaddress=<IP_DO_WSL>
            ```
    7.  **(Opcional) Libere a porta no Firewall do Windows:** Se tiver problemas de conexão, adicione uma regra de entrada TCP para a porta `6379` no "Firewall do Windows Defender com Segurança Avançada".

### 📦 Microsoft C++ Build Tools (Para Windows)

Essencial para compilar certas dependências Python (ex: `chromadb`) que exigem **"Microsoft Visual C++ 14.0 or greater"**.

* **Instalação:**
    1.  Acesse: [https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
    2.  Baixe e execute o instalador do **"Microsoft C++ Build Tools" (a versão mais recente)**.
    3.  Quando o instalador abrir, em "Cargas de trabalho", **MARQUE A CAIXA "Desenvolvimento para desktop com C++"**.
    4.  No painel "Detalhes da instalação" (à direita), confirme que "MSVC v143 - VS 2022 C++ x64/x86 build tools" (ou versão similar) e "SDK do Windows 10/11" estão marcados.
    5.  Clique em `Instalar`.
    6.  **Reinicie seu computador** após a instalação.

---

## 🚀 Configuração e Execução do Projeto

### 1. Preparar o Projeto

1.  **Clone o Repositório (se aplicável) ou crie a estrutura de arquivos:**
    Certifique-se de que todos os arquivos e diretórios estão na sua máquina, seguindo a estrutura:
    ```
    crewai_clinic_system/
    ├── app.py
    ├── crew_orchestrator.py
    ├── last_run_results.json
    ├── .env
    ├── project_status.json
    ├── requirements.txt
    ├── crew_config/
    │   ├── __init__.py
    │   ├── agents.py
    │   └── tasks.py
    ├── project_spec/
    │   ├── der_documentation.md
    │   ├── system_flow.md
    │   └── technologies_and_roadmap.md
    └── templates/
        └── index.html
    ```
2.  **Navegue para o diretório raiz do projeto:**
    ```bash
    cd C:\caminho\para\seu\projeto\crewai_clinic_system
    ```

### 2. Configurar o Ambiente Python

É **fundamental** usar um ambiente virtual para isolar as dependências.

1.  **Corrija o PATH do Sistema (se `pip` não for reconhecido):**
    * Se `pip --version` ou `python --version` no seu terminal (sem `(venv)` ativo) não funcionar, adicione os caminhos `C:\Users\SeuUsuario\AppData\Local\Programs\Python\Python312` e `C:\Users\SeuUsuario\AppData\Local\Programs\Python\Python312\Scripts` (ajuste para seu usuário e versão) às "Variáveis de Ambiente do Sistema" do Windows (`Path`).
    * **REINICIE TODOS OS SEUS TERMINAIS** após ajustar o PATH.
2.  **Exclua o Ambiente Virtual Existente:**
    Se você já tem uma pasta `venv` no seu projeto, remova-a para garantir uma instalação limpa:
    * **CMD:** `rmdir /s /q venv`
    * **PowerShell:** `Remove-Item -Recurse -Force .venv`
3.  **Crie um Novo Ambiente Virtual (com Python 3.12.9):**
    Ainda no diretório raiz do projeto:
    ```bash
    py -3.12 -m venv venv
    ```
4.  **Ative o Novo Ambiente Virtual:**
    **Ative o ambiente virtual em CADA NOVO TERMINAL que for usar.** O prompt mostrará `(venv)`.
    * **CMD:** `.\venv\Scripts\activate.bat`
    * **PowerShell:** `.\venv\Scripts\Activate.ps1`
        * *(Se o PowerShell perguntar "com qual programa quero abrir" ou bloquear, execute como **ADMINISTRADOR**: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`, confirme com `Y`, feche e tente ativar novamente no terminal normal.)*
5.  **Limpe o cache do pip:**
    ```bash
    pip cache purge
    ```
6.  **Instale as Dependências do Projeto:**
    Com o ambiente virtual **ATIVO**:
    ```bash
    pip install -r requirements.txt
    pip install --upgrade crewai-tools
    ```
    *(Se o `crew_config/tasks.py` causar `ImportError`, certifique-se de que ele está atualizado com `FileReadTool`, `FileWriterTool`, `DirectoryReadTool` conforme as instruções.)*
7.  **Configure o Arquivo `.env`:**
    Abra o arquivo `.env` na raiz do projeto e preencha com suas informações. **Mantenha suas chaves API seguras!**
    ```env
    OPENAI_API_KEY="sua_chave_api_openai_aqui"
    OPENAI_MODEL_NAME="gpt-4o"

    SYSTEM_FLOW_SPEC_PATH="project_spec/system_flow.md"
    DER_SPEC_PATH="project_spec/der_documentation.md"
    TECHNOLOGIES_AND_ROADMAP_SPEC_PATH="project_spec/technologies_and_roadmap.md"
    PROJECT_STATUS_PATH="project_status.json"
    LAST_RUN_RESULTS_PATH="last_run_results.json"

    CELERY_BROKER_URL="redis://localhost:6379/0"
    CELERY_RESULT_BACKEND="redis://localhost:6379/0"

    FLASK_SECRET_KEY="sua_chave_secreta_flask_aqui"
    ```

### 3. Iniciar os Serviços do Sistema (Três Terminais Separados)

Você precisará de **três terminais separados** (ou abas/janelas) para rodar o sistema. **Ative o ambiente virtual (`(venv)`) em cada um deles!**

1.  **Terminal 1: Iniciar o Servidor Redis**
    * **No WSL (Ubuntu):**
        ```bash
        sudo systemctl start redis-server # Ou `redis-server`
        ```
    * Deixe este terminal rodando. Se houver erros, revise a instalação do Redis.

2.  **Terminal 2: Iniciar o Worker Celery**
    * **Ative o ambiente virtual.**
    * Inicie o worker Celery:
        ```bash
        celery -A app.celery worker --loglevel=info
        ```
    * Deixe este terminal rodando. Se o Celery não se conectar ao Redis, verifique o Terminal 1 e o firewall.

3.  **Terminal 3: Iniciar o Servidor Flask**
    * **Ative o ambiente virtual.**
    * Inicie o aplicativo Flask:
        ```bash
        python app.py
        ```
    * Deixe este terminal rodando. Ele mostrará o endereço para acessar o app.

---

### 4. Acessar o Aplicativo Web

1.  Abra seu navegador web.
2.  Digite o endereço fornecido pelo servidor Flask (geralmente `http://127.0.0.1:5000/`).

Você deverá ver a interface do sistema de orquestração de projetos CrewAI!