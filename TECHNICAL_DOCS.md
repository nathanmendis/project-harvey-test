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

-   **Agent Framework**: LangGraph
    -   Implements a state machine for the AI agent.
    -   **Nodes**: `harvey_node` (LLM decision making), `tool_node` (Action execution).
    -   **State**: `HarveyState` (TypedDict) manages conversation history, context, and traces.

-   **LLM Provider**: Google Gemini 2.5 Flash
    -   Accessed via `langchain-google-genai`.
    -   Selected for high speed and cost-effectiveness.

-   **Memory & State Management**:
    -   **Redis**: Stores short-term conversation state and agent checkpoints for low-latency retrieval.
    -   **SQLite**: Persistent storage for application data (Users, Candidates, Policies) and long-term logs (`GraphRun`).

-   **RAG (Retrieval-Augmented Generation)**:
    -   **Vector Store**: FAISS (Local CPU version).
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
    -   Returns the tool output to the graph state.
4.  **Loop**: The graph loops back to the Harvey Node with the tool output.
5.  **End**: Returns the final text response to the user.

### Tools (`core/tools/`)
-   `add_candidate`: Creates a new candidate record.
-   `create_job_description`: Saves a new job role.
-   `schedule_interview`: Creates an interview record.
-   `send_email`: Logs an email action.
-   `search_knowledge_base`: Semantic search over Candidates and Job Roles.
-   `policy_search_tool`: RAG search over indexed Policy documents.

## 4. RAG Pipeline

### Indexing
-   **Candidates/Jobs**: `core/management/commands/index_data.py` script iterates DB and adds embeddings to FAISS.
-   **Policies**: `core/services/policy_indexer.py` handles file parsing (PDF/Docx/Txt) and URL scraping. It chunks text and updates the vector store in real-time.

### Retrieval
-   The agent uses `search_knowledge_base` or `policy_search_tool`.
-   Query is embedded and compared against the FAISS index.
-   Top-k relevant chunks are returned as context to the LLM.

## 5. Security

-   **Authentication**: Standard Django Auth.
-   **Authorization**:
    -   `@user_passes_test(is_org_admin)` decorator restricts admin panel access.
    -   Data isolation: All queries are filtered by `request.user.organization`.
