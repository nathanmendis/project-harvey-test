# Technical Documentation: Project Harvey

## 1. System Architecture

Project Harvey is a modular, agentic AI application built on a robust Django backend. It integrates advanced LLM capabilities with a local knowledge base to provide intelligent HR assistance.

### Core Components

-   **Backend Framework**: Django 5.1 (ASGI with Daphne)
    -   Handles HTTP requests, WebSocket connections (future-proofing), and database ORM.
    -   **Apps**:
        -   `core`: Contains models, tools, LLM logic, and API endpoints.
        -   `adminpanel`: Custom administrative interface for managing organizations, users, and policies.
        -   `theme`: Tailwind CSS configuration.
    -   **URL Routing**:
        -   Root `/` -> Public Landing Page (with login redirects).
        -   `/app/` -> Authenticated Chat Interface.

-   **Agent Framework**: LangGraph
    -   Implements a state machine for the AI agent.
    -   **Nodes**: `harvey_node` (LLM decision making), `tool_node` (Action execution).
    -   **State**: `HarveyState` (TypedDict) manages conversation history, context, and traces.

-   **LLM Provider**: Dual-Stack Support
    -   **Groq (Primary)**: Uses `llama-3.3-70b-versatile` for ultra-fast inference. Used if `GROQ_API_KEY` is present.
    -   **Google Gemini (Fallback)**: Uses `gemini-2.5-flash` if Groq is unavailable.
    -   Accessed via `langchain-groq` and `langchain-google-genai`.

-   **Memory & State Management**:
    -   **SQLite (`checkpoints.db`)**: Stores conversation state and agent checkpoints (Active configuration).
    -   **Redis**: Optional/Legacy configuration for state persistence (currently disabled in favor of SQLite).

-   **RAG (Retrieval-Augmented Generation)**:
    -   **Vector Store**: PostgreSQL + pgvector (Dockerized).
    -   **Embeddings**: `all-MiniLM-L6-v2` (via `sentence-transformers`).
    -   **Indexing**: Custom services to index `Candidate`, `JobRole`, and `Policy` data.

## 2. Data Models

The data layer is refactored into a modular package `core/models/`.

### Organization & Users (`core/models/organization.py`)
-   **Organization**: Top-level entity isolating data (multi-tenancy support).
-   **User**: Custom user model extending `AbstractUser`.
    -   Roles: `org_admin`, `employee`, `hr`.
    -   `has_chat_access`: Boolean flag for chatbot permission.

### Recruitment (`core/models/recruitment.py`)
-   **Candidate**: Stores applicant details, skills, and resume path. Linked to Organization.
-   **JobRole**: Job descriptions and requirements.
-   **Interview**: Scheduled interview events.
-   **EmailLog**: Audit trail of emails sent by the agent.

### Chatbot (`core/models/chatbot.py`)
-   **Conversation**: Groups messages into a session.
-   **Message**: Individual chat messages (User/AI).
-   **GraphRun**: Detailed execution logs of the agent (Trace, Status, Output).

### Policy Management (`core/models/policy.py`)
-   **Policy**: Metadata for HR policies (Title, Source Type: File/URL).
-   **PolicyChunk**: Text chunks extracted from policies, stored with metadata for RAG.

## 3. Agent Workflow

The agent logic is defined in `core/llm_graph/`.

### Graph Structure
1.  **Start**: Input user query.
2.  **Harvey Node**:
    -   Loads conversation history and structured context (User info, Date).
    -   Generates a response or a tool call using the `SYSTEM_PROMPT`.
    -   **Anti-Hallucination**: "Action Reality" rule enforces tool usage for DB writes.
3.  **Tool Node** (Conditional):
    -   Executes if the LLM requests a tool.
    -   Loops back to the **Harvey Node** with tool output.
4.  **Summary Node** (Conditional, if no tool):
    -   Analyzes the conversation turn.
    -   Updates the structured `context` state (goals, extracted info).
5.  **End**: Returns the final response.

### Tools (`core/tools/`)
-   `add_candidate`: Creates a new candidate record.
-   `create_job_description`: Saves a new job role.
-   `schedule_interview`: Creates an interview record.
-   `send_email`: Logs an email action.
-   `search_knowledge_base`: Semantic search over Candidates and Job Roles.
-   `policy_search_tool`: RAG search over indexed Policy documents.

## 4. RAG Pipeline

### Indexing
### Indexing
-   **Candidates/Jobs (Automatic)**: 
    -   Handled by `core/services/model_indexer.py`.
    -   Triggered by **Django Signals** (`post_save`) on `Candidate` and `JobRole`.
    -   Indexing runs in a background thread to prevent blocking the HTTP response.
-   **Policies**: `core/services/policy_indexer.py` handles file parsing (PDF/Docx/Txt) and URL scraping. It chunks text and updates the vector store in real-time.

### Retrieval
-   The agent uses `search_knowledge_base` or `policy_search_tool`.
-   Query is embedded and compared against the PostgreSQL index.
-   Top-k relevant chunks are returned as context to the LLM.

## 5. Security

-   **Authentication**: Standard Django Auth.
-   **Authorization**:
    -   `@user_passes_test(is_org_admin)` decorator restricts admin panel access.
    -   Data isolation: All queries are filtered by `request.user.organization`.
