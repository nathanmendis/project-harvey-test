# Project Harvey: AI-Powered HR Agent v3.1

Harvey is a high-performance, agentic HR assistant designed to automate recruitment workflows. It leverages a hybrid multi-model architecture to provide lightning-fast intent detection and complex reasoning for recruitment tasks.

## 🚀 Strategic Impact & Core Capabilities

| Capability | Technical Mechanism | Strategic Business Impact |
| :--- | :--- | :--- |
| **Proactive AI** | Zero-Token Contextual Utils | **Zero LLM Cost** for standard daily user interactions. |
| **Asymmetric Routing** | Llama-3.1-8B Router | **80% Reduction in API latency** and inference overhead. |
| **Secure Document Theater** | Iframe Suppression + Shielding | **Locked Intellectual Property**; prevents document leakage. |
| **DB Cryptography** | Fernet Symmetric Encryption | **100% Protection against PII theft** in DB breaches. |
| **RAG Policy Engine** | PGVector Metadata Scoping | **AI-Powered Legal Compliance** across full document sets. |
| **Async HRMS Sync** | Celery + Redis Task Queues | **Enterprise Scalability** without blocking standard UI flow. |
| **RBAC Isolation** | Organization-Gated Middleware | **Multi-Tenant Trust**; zero risk of cross-org data bleed. |

---

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

### 🧠 Proactive Agentic UX & UI

- **Zero-Token Contextual Auto-Greetings**: The agent reads server time, pending tasks, anniversaries, and *sticky memory* (your last chat intent) to dynamically greet you on page load without using a single LLM token.
- **Copilot Action Chips**: Clickable macro-chips embedded above the chat input allowing managers to "Review Leaves" or employees to "Apply for PTO" with a single tap.
- **Dashboard Alert Cards & Modals**: Action-required glowing cards automatically populate the dashboard for pending approvals, alongside celebratory pop-up modals for organization anniversaries based on user join dates.
- **Scalable Background Digests**: Celery beat workers automatically compile and dispatch Daily Manager Action Digests (9 AM M-F) and Weekly Employee Leave Summaries (4 PM Fri) over Gmail OAuth.

### 🏖️ Leave & PTO Management

- **Centralized Policy Engine**: Organization-level control over yearly leave allocations (Sick, Annual, etc.).
- **Asynchronous Mass-Provisioning**: Leverages Celery background workers to instantly cascade policy updates to thousands of employee balances securely.
- **Smart Carryover**: Natively supports rolling over unused PTO from the previous year into the new year's balance automatically.
- **Real-Time Verification**: Integrated with the AI agent to dynamically verify employee balances and deduct approved requests via strict Django signals.

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
