# Project Harvey: AI-Powered HR Agent v3.0

Harvey is a high-performance, agentic HR assistant designed to automate recruitment workflows. It leverages a hybrid multi-model architecture to provide lightning-fast intent detection and complex reasoning for recruitment tasks.

## ✨ Key Features (Version 3.0)

### 🤖 Intelligent "Hybrid Brain"
-   **Multi-Model Strategy**: Uses **Llama-3.1-8B** for instant routing and **Llama-3.3-70B** for complex tool drafting and reasoning.
-   **Deterministic Routing**: Intent classification runs at `temperature=0` for perfect reliability.
-   **Advanced Token Optimization**: Implements aggressive **history pruning**—keeping only the last 4 messages after summarization to ensure sub-second response times in long chats.

### 📅 Recruitment & Calendar Automation
-   **Google Calendar Sync**: The `schedule_interview` tool automatically creates invites on your calendar with the `{Role} Interview` format and returns clickable meeting links.
-   **IST Native**: Full support for **Indian Standard Time (IST)** localization for all scheduling and date-based queries.

### 📚 RAG (Retrieval-Augmented Generation)
-   **PGVector Knowledge Base**: Instant semantic search over candidates, job roles, and HR policies using **PostgreSQL + pgvector**.
-   **Policy Assistant**: Upload PDFs or URLs; Harvey indexes them and answers complex policy questions with source attribution.

### 🔐 Enterprise-Grade Identity
-   **Two-Tier OAuth**: Decouples simple user login from system-wide Gmail/Calendar capacities, ensuring the system can "act" reliably via a System Account.
-   **Multi-tenant Ready**: Secure data isolation at the ORM level, ensuring every response is scoped to your organization.

## 🏗️ Technical Stack

-   **Backend**: Django 5.1 (ASGI/Daphne)
-   **Agent Framework**: LangGraph (Stateful State Machines)
-   **LLMs**: Groq (Llama-3.x) & Google Gemini (Fallback)
-   **Vector Store**: PGVector (384-dim optimized)
-   **Caching/Bus**: Redis

For a deep dive into the system design and agent workflow, see [learn.md](learn.md) or [TECHNICAL_DOCS.md](TECHNICAL_DOCS.md).

## 🚀 Getting Started

1.  **Clone & Install**
    ```bash
    git clone https://github.com/nathanmendis/project-harvey.git
    poetry install
    ```
2.  **Docker Database**
    ```bash
    docker-compose up -d db redis
    ```
3.  **Run migrations**
    ```bash
    poetry run python manage.py migrate
    poetry run python manage.py index_data
    ```
4.  **Start the Brain**
    ```bash
    poetry run daphne project_harvey.asgi:application
    ```

Access the dashboard at `http://localhost:8000`.
