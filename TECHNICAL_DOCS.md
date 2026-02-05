# Technical Documentation: Project Harvey v3.0

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

- **Router/Chat (Llama-3.1-8B)**: Used for intent classification and general conversation.
- **Reasoner (Llama 4 Scout - 17B)**: The "Agentic Brain". Specialized 2026-gen model used for complex tool drafting (JSON formatting) and summarization.

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
- **Interview**: Links Candidates, Interviewers, and Organizations. Features `date_time` fields localized to **IST**.
- **CandidateJobScore**: Stores AI-generated match percentages and justifications.

### 3.3 Knowledge Base (RAG)
- **Policy**: Metadata for uploaded documents or URLs.
- **PolicyChunk**: Individual text snippets (approx. 1000 chars) stored with their 384-dimensional vector embeddings.

### 3.4 Conversation Persistence
- **Conversation**: Session container for a series of messages.
- **Message**: Individual speech acts. Content is **AES-256 encrypted** in the database.
- **GraphRun**: Logs for individual agent execution trails, including timing metrics and node traces.

---

## 4. The Agentic Workflow (`core/llm_graph/`)

The graph lifecycle is managed in `nodes.py` and `graph.py`.

### 4.1 LangGraph Nodes
1. **`router_node`**: Uses Llama-8B at `temp=0` to decide if a tool is needed.
2. **`harvey_node`**: The core "brain". It formats the prompt (splitting into Static and Dynamic components) and generates responses.
3. **`execute_node`**: Dynamically fetches functions from the `tool_registry` and invokes them.
4. **`summary_node`**: Triggers every 8 messages to compress history and prune the message list to 4 items.

### 4.2 Prompt Strategy
We use **Split Prompting**:
- **Static Prompt**: Core HR rules, anti-hallucination protocols, and formatting constraints.
- **Dynamic Prompt**: Injects real-time context: `current_goal`, `current_date` (IST), `Known Info` (memory), and `Tools`.

---

## 5. Tool Integration System (`core/tools/`)

The system uses a centralized registry to bind Python functions to the LLM.

### 5.1 Key Tools
| Tool | Functionality |
| :--- | :--- |
| `add_candidate` | Creates candidate records from raw text. |
| `add_candidate_with_resume` | Processes PDF/Docx files into candidate records. |
| `schedule_interview` | Interfaces with the database and **Google Calendar API**. |
| `search_knowledge_base` | Semantic search over internal Candidate/Job data. |
| `search_policies` | Retrieval-Augmented Generation (RAG) over HR documents. |

### 5.2 Google Workspace Integration
- **OAuth Strategy**: Uses a **System Refresh Token** for backend actions (Email/Calendar) and standard OAuth for user login.
- **Timezone**: Explicitly localized to `Asia/Kolkata` across all external triggers.

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
- **Logs**: Monitor `harvey.log` for token usage and IST localization offsets.

---
*Maintained by the Harvey Engineering Team*
