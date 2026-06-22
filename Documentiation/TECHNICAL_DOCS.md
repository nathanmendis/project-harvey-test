# Technical Documentation: Project Harvey v3.1

## 1. System Overview

Project Harvey is a state-of-the-art HR automation platform. It uses a **Hybrid Async-Sync Backend** (Django + Daphne) and a **Stateful Agentic Graph** (LangGraph) to automate complex recruitment and policy management tasks.

---

## 2. Architecture: The "Engine Room"

### 2.1 Server Stack
- **ASGI Server**: `Daphne`. Handles both HTTP and WebSockets.
- **Message Bus**: `Redis`. Managed by `Django Channels` for real-time inter-process communication.
- **AI Orchestrator**: `LangGraph`. Manages the directed cyclic graph logic.
- **Persistence**: `PostgreSQL` + `PGVector` for relational data and semantic embeddings.

### 2.2 Model Selection Logic
To optimize for both speed and reasoning depth, we use a tiered model strategy:

- **Router/Chat (Llama-3.1-8B)**: For intent classification and general conversation.
- **Reasoner (Llama 4 Scout - 17B)**: The specialized agentic model used for complex tool drafting and reasoning.

---

## 3. Data Models Deep-Dive (`core/models/`)

The database is divided into logical functional areas:

### 3.1 Organization & Identity
- **Organization**: The central tenant. Every user and data point is linked here.
- **User**: Custom model extending `AbstractUser`. Includes roles (`admin`, `hr`, `employee`) and `has_chat_access` permissions.
- **Invite**: UUID-based token system for secure onboarding.

### 3.2 Recruitment Engine
- **Candidate**: Stores profiles, contact info, and parsed JSON metadata.
- **JobRole**: Stores job descriptions and requirement strings.
- **Interview**: Links Candidates, Interviewers, and Organizations. Features `date_time` fields dynamically populated using the organization's customized timezone, falling back to Google Calendar defaults when necessary.
- **CandidateJobScore**: Stores AI-generated match percentages and justifications.

### 3.3 Knowledge Base (RAG)
- **Policy**: Metadata for uploaded documents or URLs.
- **PolicyChunk**: Individual text snippets (approx. 1000 chars) stored with their 384-dimensional vector embeddings.

### 3.4 Conversation Persistence
- **Conversation**: Session container for a series of messages, strictly scoped to an `organization_id` to ensure tenant data isolation.
- **Message**: Individual speech acts. Content is **AES-256 encrypted** in the database.
- **GraphRun**: Logs for individual agent execution trails, including timing metrics and node traces.

### 3.5 Leave Management
- **OrganizationLeavePolicy**: Defines the default yearly allocation (e.g. 15 Sick Days in 2026) per organization.
- **LeaveBalance**: Tracks an individual employee's `total_allocated`, `used`, and dynamically calculates `remaining` days. Automatically handles carryovers from previous years.
- **LeaveRequest**: Records employee PTO requests. Includes a `post_save` signal that securely deducts days from the `LeaveBalance` only upon "approved" status.
- **LeaveSystemConfig**: Manages secure edit tokens for the token-gated Admin Panel UI.

---

## 4. The Agentic Workflow (`core/ai/agentic/graph/`)

The graph lifecycle is managed within the `core/ai/agentic/graph/nodes/` package.

### 4.1 LangGraph Nodes
1. **`router.py`**: Intent Classifier (Llama-8B) with prioritized hints.
2. **`harvey.py`**: Core reasoner with context flattening and LLM bypass logic.
3. **`execute.py`**: Invokes tools from the registry and handles email drafting.
4. **`summary.py`**: Compresses history after 8 turns to maintain context efficiency.
5. **`utils.py`**: Shared helpers including **token usage logging**.

### 4.2 Prompt Strategy
We use **Split Prompting**:
- **Static Prompt**: Core HR rules, anti-hallucination protocols, and formatting constraints.
- **Dynamic Prompt**: Injects real-time context: `current_goal`, `current_date` (IST), `Known Info` (memory), and `Tools`.

---

## 5. Tool Integration System (`core/ai/agentic/tools/`)

The system uses a centralized registry to bind Python functions to the LLM.

### 5.1 Key Tools
| Tool | Functionality |
| :--- | :--- |
| `add_candidate` | Creates candidate records from raw text. |
| `add_candidate_with_resume` | Processes PDF/Docx files into candidate records. |
| `schedule_interview` | Interfaces with the database and **Google Calendar API**. |
| `search_knowledge_base` | Semantic search over internal Candidate/Job data. |
| `search_policies` | Retrieval-Augmented Generation (RAG) over HR documents. |

### 5.2 Google Workspace & Tool Enhancements
- **Enhanced Resolution**: All tools (Email, Calendar) use shared utilities to resolve names/usernames to emails with multiple-match handling.
- **OAuth Strategy**: System Refresh Token for backend actions; standard OAuth for user sessions.
- **Timezone**: Dynamic timezone resolution via the `Organization` model, ensuring tools like `schedule_interview` create precise calendar events regardless of locale.

---

## 6. Architectural Decisions & Trade-offs (Defense of Tech Stack)

### 6.1 Why Daphne (ASGI) vs Gunicorn (WSGI)?
- **Gunicorn**: Synchronous. Every connection blocks a worker process. Not suitable for WebSockets.
- **Daphne**: Asynchronous. Can handle thousands of persistent WebSocket connections with minimal resources, enabling real-time "thinking traces" from the AI.

### 6.2 Why LangGraph vs Standard LangChain?
- **LangChain**: Excellent for linear chains but fails gracefully on cyclic logic (retries, self-correction).
- **LangGraph**: Models the agent as a **State Machine**. It persists state (checkpoints) at every step, allowing the AI to "go back" or "loop" to fix tool-input errors without losing context.

### 6.3 Why PGVector vs Dedicated Vector DBs (Chroma/Pinecone)?
- **Chroma/Pinecone**: Require separate infrastructure and external syncing logic.
- **PGVector**: Keeps vectors inside PostgreSQL. This allows for **Relational Semantic Search**: "Find me candidates with Python skills (relational) AND a resume close to this JD (semantic)" in a single ACID-compliant query.

### 6.4 Why Django vs FastAPI/Flask?
- **FastAPI/Flask**: Lightweight but require manually integrating Auth, Admin, and ORM libraries.
- **Django**: "Batteries Included". Provides a robust admin panel, production-ready auth, and the most mature WebSocket integration (Channels) for Python.

### 6.5 Why Hybrid Models (8B/Scout)?
- **Generic 70B Model**: High latency and resource-heavy for free-tier quotas.
- **Llama 4 Scout (17B)**: A specialized agentic model that provides superior tool-calling accuracy while being 4x smaller, significantly increasing your rate-limit headroom.

---

## 7. API & Protocol Specifications

### 7.1 WebSocket Protocol (`/ws/chat/`)
- **Protocol**: JSON over WS.
- **Frames**:
    - `chat_message`: User input.
    - `trace`: Optional debug info pushed by the AI.
    - `ai_message`: Final formatted response.

### 7.2 REST APIs
- `GET /api/conversations/`: Returns user session history.
- `GET /api/conversations/<id>/messages/`: Returns paginated, decrypted message history.
- `POST /api/policies/<id>/index/`: Triggers the background indexing thread.

---

## 8. Developer Operations (DevOps)

### 8.1 Setup
1. `poetry install`
2. `docker-compose up -d db redis`
3. `python manage.py migrate`
4. `python manage.py index_data` (Initial Vector Seed)

### 8.2 Verification
- **Unit Tests**: `poetry run pytest`.
- **Router Audit**: `poetry run pytest tests/test_router_architecture.py`.
- **Logs**: Monitor `harvey.log` for **real-time token usage** (Prompt/Completion/Total) and IST offsets.

---

## 9. System Health Monitoring & Admin Utilities

### 9.1 Diagnostic Dashboard
Administrators can access the system health dashboard at `/settings/health/` (defined in `adminpanel/views/health.py`):
- **Redis Health**: Verifies connection and tracks real-time read/write latency.
- **Celery Verification**: Counts active worker processes registered to the task queue.
- **Environment Checks**: Verifies availability of API keys (e.g., `GROQ_API_KEY`) and system configurations.
- **UI Design**: Single-card professional dashboard featuring premium custom SVG-animated loaders (no emojis used).

### 9.2 Google OAuth System Token Generator
Superusers and staff can initiate a system-wide Google OAuth consent flow directly from the Django Admin Panel home page (`/admin/`):
- **Dashboard Widget**: Integrates a widget on the main dashboard (`custom_index.html`) using a customized `admin.site.index_template` override.
- **System Callback Routing**: Authenticates with full system scopes and prompts consent. The callback handles `is_system_token_flow` and renders a high-contrast display page (`system_token_display.html`) with the new refresh token and copy-paste instructions for the `.env` file.

---
*Maintained by the Harvey Engineering Team*
