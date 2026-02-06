# Agent Working & System Internals

This document provides a deep dive into the internal workings of Project Harvey, specifically focusing on the Agent Pipeline, View Functions, Data Models, and Tools.

## 1. The Agentic Brain (LangGraph Architecture)

The core "thinking" engine resides in `core/ai/agentic/graph/`. It is implemented as a **Directed Cyclic Graph (DCG)** where state is persisted at every transition point.

### 1.1 `HarveyState` (The Persistent Context)
The agent operates on a `TypedDict` state object that survives across WebSocket frames:
- **`messages`**: An append-only list containing `HumanMessage`, `AIMessage`, `SystemMessage`, and `ToolMessage`.
- **`user_id`**: Integer PK of the Django user, used for scoped data lookups.
- **`intent`**: Classified by the Router ('chat' for greetings/thanks, 'tool' for anything requiring tool invocation).
- **`target_tool`**: A string hint identifying which tool is most likely needed.
- **`pending_tool`**: A dictionary containing the tool name and validated arguments from the Reasoner.
- **`context`**: A structured dictionary that acts as the "Working Memory":
    - `current_goal`: A concise string describing the user's primary objective.
    - `extracted_info`: A key-value store of entities (e.g., `candidate_name: "Alice"`). **Critical**: This is flattened into a plaintext list during `harvey_node` execution to save tokens.
- **`trace`**: A list of execution metadata (ms duration, node hits) used to power the real-time "Thinking" logs in the UI.

### 1.2 The Multi-Model Tiered Strategy
To balance costs, latency, and reasoning depth, we employ a hybrid strategy:
- **Router (Llama-3.1-8B)**: Optimized for speed (<400ms). Used at `temp=0` to ensure deterministic intent classification.
- **Reasoner (Llama 4 Scout - 17B)**: Optimized for agentic "tool-calling" accuracy. It outperforms generic 70B models in JSON schema adherence while maintaining a smaller footprint.
- **Summarizer (Llama-3.1-8B)**: Used for post-interaction memory compression.

---

## 2. Node-by-Node Process Logic

### 2.1 `router_node` (`router.py`)
1. **Trigger**: Every user message hits this node first.
2. **Logic**: It looks at the message syntax. If a user says "send" while an email draft exists, it force-routes to the `send_email_tool`.
3. **LLM Call**: Otherwise, it invokes the 8B model to classify intent.
4. **HINTS**: It generates a `target_tool` hint. This is passed to the next node to guide the reasoner, reducing the search space for tool selection.

### 2.2 `harvey_node` (`harvey.py`)
This is the central reasoning node.
1. **The LLM Bypass**: If the previous node was `execute_node`, it finds a `ToolMessage` at the end of the history. It **bypasses the LLM entirely**, returning the raw tool output. This prevents the LLM from rewriting or "explaining away" important links/IDs.
2. **Prompt Strategy**:
    - **Static Prompt**: Core HR identity and behavior rules (No hallucinations, IST time zone).
    - **Dynamic Prompt**: Injected live state (Extracted Info, Active Goal, Current IST Time).
3. **Context Flattening**: Converts the `extracted_info` dict into a compact string (`- Name: Bob\n- Role: Python`). This reduces prompt tokens by ~40% compared to raw JSON.

### 2.3 `execute_node` (`execute.py`)
1. **Validation**: Checks if a tool call exists in the message.
2. **Registry Mapping**: It fetches the Python function from `tools_registry.py`.
3. **Execution**: Runs the tool with `organization` context (ensuring Alice can't see Bob's candidates).
4. **Error Handling**: If a tool fails (e.g., "Candidate not found"), it returns the error string as a `ToolMessage`. The Graph then loops back to `harvey_node`, allowing the AI to "read" the error and try a different approach.

### 2.4 `summary_node` (`summary.py`)
1. **Trigger**: Activates when `len(messages) >= 8`.
2. **Aggressive Pruning**: It generates a high-level summary of the chat, stores it in `context`, and then **deletes all but the last 4 messages**.
3. **Benefit**: This keeps the token window small, ensuring performance doesn't degrade even in hours-long conversations.

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
    -   `vector_id`: ID in the **PGVector** index.

---

## 4. The Tool Ecosystem (`core/ai/agentic/tools/`)

### 4.1 Shared Utility Logic (`utils.py`)
All tools depend on a shared logic layer for data normalization:
- **`resolve_user_emails`**: 
    1. First, it regex-checks if the input *is* an email. If so, it returns it directly (External Support).
    2. Otherwise, it searches the Django `User` table by `name` or `username`.
- **`resolve_candidate_emails`**: Similar to above, but queries the `Candidate` table.
- **Multiple Match Handling**: If a name search returns >1 result, the tool does **not** pick one. It returns an error message listing the options, forcing the agent (or user) to be more specific.

### 4.2 Recruitment Tools (`recruitment_tools.py`)
- **`search_knowledge_base`**: Uses the **PGVector** similarity search. It converts the user's query into a 384-dim vector using `all-MiniLM-L6-v2` and finds the closest candidates.

### 4.3 Email & Calendar (`email_tool.py`, `calendar_tool.py`)
- **Gmail/Calendar OAuth**: Uses the **System Refresh Token** provided in `.env`.
- **Drafting vs Sending**: 
    - If the user says "draft", the agent populates `draft_email` in the state.
    - If the agent calls `send_email_tool`, it executes immediately via API.

---

## 5. Audit & Performance (The `GraphRun` System)

Every time the agent "thinks", a record is created in the `GraphRun` model:
- **Node Traces**: JSON blob of every node visited and its latency.
- **Token Logs**: Granular logs of Prompt vs Completion tokens per LLM call.
- **Final Result**: The absolute state of the graph after the run.
- **Debugging**: Admins can view these in the `/admin/` panel to debug failing tool-calls or long response times.
