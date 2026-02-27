# Project Harvey: AI-Powered HR Agent v3.1

Harvey is a high-performance, agentic HR assistant designed to automate recruitment workflows. It leverages a hybrid multi-model architecture to provide lightning-fast intent detection and complex reasoning for recruitment tasks.

## ✨ Key Features (Version 3.0)

### 🤖 Intelligent "Hybrid Brain"

- **Multi-Model Strategy**: Uses **Llama-3.1-8B** for instant routing and **Llama 4 Scout (17B)** for complex tool drafting and agentic reasoning.
- **Deterministic Routing**: Intent classification runs at `temperature=0` using the 8B model.
- **Advanced Token Optimization**: Implements **context flattening** and aggressive history pruning to maintain sub-second response times.

### 📅 Recruitment & Calendar Automation

- **Enhanced Tool Resolution**: Directly resolve names/usernames to emails with support for **multiple match detection**.
- **Google Calendar Sync**: The `schedule_interview` tool automatically creates invites on your calendar and returns clickable meeting links.
- **Dynamic Organization Timezones**: Full support for customizable timezones per organization, ensuring accurate and precise interview scheduling regardless of geographic location. Fallbacks to Google Calendar default timezones are included for robustness.

### 📚 RAG (Retrieval-Augmented Generation)

- **PGVector Knowledge Base**: Semantic search using **PostgreSQL + pgvector** and **PyTorch-based all-MiniLM-L6-v2** embeddings.
- **Policy Assistant**: Index PDFs or URLs and get answers with source attribution.

### 🔐 Enterprise-Grade Identity

- **Two-Tier OAuth**: Decouples simple user login from system-wide Gmail/Calendar capacities, ensuring the system can "act" reliably via a System Account.
- **Multi-tenant Ready**: Secure data isolation at the ORM level, ensuring every response is scoped to your organization.
- **Strict Database Integrity**: Guaranteed organization-level scoping (`organization_id`) for Invites, Conversations, and HRMS System Configurations, preventing data leakage and ensuring robust tenant routing.

## 🏗️ Technical Stack

- **Backend**: Django 5.1 (ASGI/Daphne)
- **Agent Framework**: LangGraph (Stateful State Machines)
- **LLMs**: Groq (Llama-3.x) & Google Gemini (Fallback)
- **Vector Store**: PGVector (384-dim optimized)
- **Caching/Bus**: Redis

## 🔗 HR System Integration

Harvey supports integration with existing HRMS platforms (Workday, BambooHR, SAP SuccessFactors, etc.) using a **scheduled batch sync architecture** for optimal performance and data security. The built-in HRMS configuration dashboard allows administrators to manage sync keys, set up templates, and review status per organization.

**Key Benefits:**

- ⚡ Sub-second response times (local data copy)
- 🔒 Data sovereignty and compliance (GDPR-ready)
- 🛡️ Offline capability (works during HRMS downtime)
- 💰 Cost-effective (minimal API calls)

**Documentation:**

- [HR Integration Architecture](Documentiation/HR_INTEGRATION.md) - Complete implementation guide
- [Visual Diagrams](Documentiation/HR_INTEGRATION_DIAGRAMS.md) - Architecture diagrams and workflows

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
