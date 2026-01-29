# Project Harvey: AI-Powered HR Agent

Harvey is an intelligent HR assistant designed to streamline recruitment workflows. It leverages a graph-based agentic architecture to manage context, execute tools, and retrieve information from a local knowledge base.

## ✨ Key Features

### 🤖 Intelligent Agent
-   **Context-Aware**: Built with **LangGraph**, Harvey maintains conversation state, remembers goals, and adapts to topic shifts.
-   **Multi-Session Memory**: Supports **Multiple Conversations** per user. Switch between chat sessions seamlessly with isolated context and full history.
-   **Anti-Hallucination**: Implements "Action Reality" protocols to ensure the agent only claims actions it has actually performed via tools.
-   **Structured Memory**: Uses **Redis** for low-latency conversation history and context retrieval.

### 📚 RAG (Retrieval-Augmented Generation)
-   **Candidate & Job Search**: Semantically searches for candidates and job roles using **PostgreSQL (pgvector)** and **Sentence Transformers**.
-   **Policy Assistant**: Upload HR policies (PDF, Docx, TXT) or URLs. Harvey automatically indexes them and answers policy-related questions.

### 🛠️ Tool Integration
-   **Recruitment**: Add candidates, create job descriptions, shortlist candidates.
-   **Operations**: Schedule interviews, draft and send emails.
-   **Knowledge Base**: Real-time semantic search over organizational data.

### 🖥️ Admin Panel & UI
-   **Public Landing Page**: Premium, responsive landing page with project information.
-   **Dashboard**: Overview of organization stats (Users, Staff, Admins).
-   **Employee Management**: Add/Remove employees, toggle chatbot access, manage roles.
-   **Policy Management**: Upload, view, and re-index HR policies.
-   **Modern UI**: Styled with **Tailwind CSS** for a responsive and premium feel.

### 🧠 Automatic Knowledge Base
-   **Auto-Indexing**: Candidates and Job Roles are automatically indexed into the vector store upon creation, enabling instant semantic search availability.

## 🏗️ Architecture

-   **Backend**: Django 5.1 (ASGI)
-   **Agent**: LangGraph + Groq (Llama 3.3) / Google Gemini 2.5 Flash
-   **Vector Store**: PostgreSQL + pgvector (Dockerized)
-   **Database**: SQLite (Data) + Redis (State)

For a deep dive into the system design, data models, and agent workflow, see the [Technical Documentation](TECHNICAL_DOCS.md).

## 🚀 Getting Started

### Prerequisites
-   Python 3.10+
-   [Poetry](https://python-poetry.org/)
-   [Redis](https://redis.io/) (Port 6379)
-   [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 🐳 Docker Setup (Short Version)
1.  **Download & Install**: Get Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/).
2.  **Run Docker**: Start the application and ensure the engine is running.
3.  **Verify**: Run `docker --version` in your terminal.

### Setup from Git

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/nathanmendis/project-harvey.git
    cd project-harvey
    ```

2.  **Install Dependencies**
    ```bash
    poetry install
    ```

3.  **Environment Setup**
    Create a `.env` file in the root directory:
    ```env
    GOOGLE_API_KEY=your_api_key_here
    ```

4.  **Database Setup**
    ```bash
    poetry run python manage.py migrate
    poetry run python manage.py createsuperuser
    ```

    **Accessing the Database Container:**
    To manually inspect the PostgreSQL database running in Docker:
    ```bash
    docker exec -it project-harvey-test-db-1 psql -U postgres -d postgres
    ```

5.  **Index Knowledge Base**
    Populate the vector store with initial data:
    ```bash
    poetry run python manage.py index_data
    ```

6.  **Run the Server**
    ```bash
    poetry run daphne project_harvey.asgi:application
    ```
    Access the app at `http://127.0.0.1:8000`.

### Keeping Updated

To pull the latest changes from the repository and ensure your environment is up to date:

```bash
git pull origin main
poetry install
poetry run python manage.py migrate
```

## 🧪 Testing

-   **Run Unit Tests**: `poetry run pytest`
-   **Verify Vector Search**: `poetry run python core/llm_graph/test_search.py`
-   **Verify Context Switching**: `poetry run python core/llm_graph/test_context.py`
