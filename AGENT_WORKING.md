# Agent Working & System Internals

This document provides a deep dive into the internal workings of Project Harvey, specifically focusing on the Agent Pipeline, View Functions, Data Models, and Tools.

## 1. Agent Pipeline (`core/llm_graph/`)

The core of Harvey is a state machine built with **LangGraph**. It manages the conversation flow, decision-making, and tool execution.

### State Schema (`HarveyState`)
The agent maintains a typed state dictionary throughout the conversation:
-   `messages`: List of all messages (User, AI, System, Tool outputs).
-   `user_id`: ID of the current user.
-   `context`: A dictionary containing:
    -   `current_goal`: The active objective (e.g., "Scheduling an interview").
    -   `last_active_topic`: To detect context switches.
    -   `extracted_info`: Structured data extracted from user input (e.g., candidate names, dates).
-   `pending_tool`: Stores a tool call request from the LLM to be executed by the Tool Node.
-   `trace`: A log of internal events (node execution times, errors) for debugging.

### Graph Nodes

#### 1. `harvey_node` (The Brain)
-   **Input**: Current state.
-   **Process**:
    1.  Constructs a prompt using `SYSTEM_PROMPT` (in `harvey_prompt.py`).
    2.  Injects dynamic context: Current Goal, Last Topic, Extracted Info, and Available Tools.
    3.  Calls Google Gemini 2.5 Flash.
    4.  **Anti-Hallucination**: The system prompt enforces "Action Reality" — the agent is forbidden from claiming it did something unless it actually calls a tool.
-   **Output**:
    -   If the LLM generates text: Returns an `AIMessage`.
    -   If the LLM requests a tool: Sets `pending_tool` in the state.

#### 2. `should_execute` (Conditional Edge)
-   **Logic**: Checks if `pending_tool` is set.
    -   **True**: Routes to `TOOL` node.
    -   **False**: Routes to `SUM` node (Summary).

#### 3. `execute_node` (The Hands)
-   **Input**: State with a `pending_tool`.
-   **Process**:
    1.  Looks up the tool function in `tool_registry`.
    2.  Executes the tool with the provided arguments and the current `user` object.
    3.  Catches any errors.
-   **Output**: Returns a `FunctionMessage` containing the tool's JSON output.

#### 4. `summary_node` (The Memory)
-   **Input**: Updated message history.
-   **Process**:
    1.  Analyzes the conversation to update `current_goal` and `extracted_info`.
    2.  Uses a smaller LLM call (or logic) to keep the context fresh.
-   **Output**: Updates the `context` key in the state.

---

## 2. View Functions

### Core Views (`core/views.py`)

| Function | Description |
| :--- | :--- |
| `login_view` | Handles user authentication. Redirects users based on their role (`org_admin` -> Dashboard, `employee` -> Chat). |
| `chat_page` | Renders the main chat interface (`core.html`). Checks `has_chat_access` permission. |
| `chat_with_llm` | **API Endpoint**. Receives JSON POST requests with `prompt`. Invokes the LangGraph agent via `generate_llm_reply` and returns the response. |
| `CustomLogoutView` | Handles user logout and clears session memory. |

### Admin Panel Views (`adminpanel/views.py`)

| Function | Description |
| :--- | :--- |
| `admin_dashboard` | Displays organization overview: Total users, staff count, admin count. |
| `add_employee` | Form to create a new `User`. Sets initial password, role, and chatbot access. |
| `manage_employees` | Lists all non-superuser employees in the organization. |
| `remove_employee` | Deletes a user account. Prevents deletion of other admins. |
| `toggle_chat_access`| Toggles the `has_chat_access` boolean for a user. |
| `toggle_admin_role` | Promotes/Demotes a user between `employee` and `org_admin`. |
| `add_org_admin` | Allows an existing admin to create another admin account. |
| `manage_org_admins` | Lists all admins in the organization. |
| `search_employee` | JSON API for searching employees by name/email (used in UI search bars). |
| `manage_policies` | Lists all uploaded HR policies. |
| `add_policy` | Form to upload a file (PDF/Docx/Txt) or URL. Triggers background indexing. |
| `reindex_policy` | Manually triggers the `PolicyIndexer` to re-process a policy. |
| `delete_policy` | Deletes a policy and its associated vector chunks. |

---

## 3. Data Models (`core/models/`)

### Organization (`core/models/organization.py`)
-   **`Organization`**: The tenant. All data is siloed by this ID.
-   **`User`**: Custom user model.
    -   `role`: Determines access level (`org_admin`, `hr`, `employee`).
    -   `has_chat_access`: Controls access to the chat interface.

### Recruitment (`core/models/recruitment.py`)
-   **`Candidate`**: Represents a job applicant.
    -   `skills`: JSON list of skills.
    -   `status`: 'pending', 'interviewing', 'hired', etc.
-   **`JobRole`**: Open positions.
-   **`Interview`**: Links `Candidate`, `Interviewer` (User), and `DateTime`.
-   **`EmailLog`**: Audit log of all emails sent by the agent.

### Chatbot (`core/models/chatbot.py`)
-   **`Conversation`**: A chat session. Stores `memory_state` (Redis backup).
-   **`Message`**: Individual messages for history.
-   **`GraphRun`**: **Critical for Debugging**. Logs every execution of the agent, including the full trace of nodes visited, inputs, outputs, and errors.

### Policy (`core/models/policy.py`)
-   **`Policy`**: Metadata for a document.
    -   `source_type`: 'upload' or 'url'.
    -   `status`: 'indexing', 'indexed', 'failed'.
-   **`PolicyChunk`**: The actual content used for RAG.
    -   `text`: A segment of the document.
    -   `vector_id`: ID in the FAISS vector store.

---

## 4. Tools (`core/tools/`)

Tools are Python functions decorated with `@tool`. They are the only way the agent can interact with the database or outside world.

| Tool | Functionality |
| :--- | :--- |
| **`add_candidate`** | Creates a `Candidate` record. Checks for duplicates by email. |
| **`create_job_description`** | Creates a `JobRole` record. |
| **`schedule_interview`** | Creates an `Interview` record. Validates datetime format. |
| **`send_email`** | Creates an `EmailLog` record. (In production, this would send a real email). |
| **`shortlist_candidates`** | Filters candidates by matching skills in their profile against a provided list. |
| **`search_knowledge_base`** | **RAG Tool**. Embeds the query and searches the FAISS vector store for relevant `Candidate` or `JobRole` chunks. Returns the top 3 matches. |

### How Tools Work
1.  **Definition**: Defined in `core/tools/base.py` (and others).
2.  **Registration**: Added to `AVAILABLE_TOOLS` in `core/llm_graph/tools_registry.py`.
3.  **Binding**: Bound to the LLM model so it knows their schemas (JSON arguments).
4.  **Invocation**: Called by `execute_node` when the LLM outputs a tool call.
