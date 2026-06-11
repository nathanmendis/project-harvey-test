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
- **`requires_approval`**: A boolean flag identifying if the current action is paused waiting for user input.
- **`context`**: A structured dictionary that acts as the "Working Memory":
- **`trace`**: A list of execution metadata (ms duration, node hits) used to power the real-time "Thinking" logs in the UI.

### 1.2 The Multi-Model Tiered Strategy & Optimization
To balance costs, latency, and reasoning depth, we employ a hybrid strategy:
- **Router (Llama-3.1-8B)**: Optimized for speed (<400ms). Used at `temp=0` to ensure deterministic intent classification. We bypass formatting instructions in favor of manual JSON parsing to keep router prompt sizes under 250 tokens.
- **Reasoner (Llama 4 Scout - 17B)**: Optimized for agentic "tool-calling" accuracy. It dynamically loads only the router's target tool schema, keeping reasoning prompt sizes under 500 tokens.
- **Summarizer (Llama-3.1-8B)**: Used for post-interaction memory compression.

---

## 2. Node-by-Node Process Logic

### 2.1 `router_node` (`router.py`)
1. **Trigger**: Every user message hits this node first.
2. **Logic**: It looks at the message syntax. If a user says "send" while an email draft exists, it force-routes to the `send_email_tool`.
3. **LLM Call**: Otherwise, it invokes the 8B model to classify intent and manually parses the JSON response.
4. **HINTS**: It generates a `target_tool` hint. This is passed to the next node to guide the reasoner.

### 2.2 `harvey_node` (`harvey.py`)
This is the central reasoning node.
1. **The LLM Bypass**: If the previous node was `execute_node`, it finds a `ToolMessage` at the end of the history. It **bypasses the LLM entirely**, returning the raw tool output. This prevents the LLM from rewriting or "explaining away" important links/IDs.
2. **Human-in-the-Loop Confirmation**: Sensitive tools (such as leaves, calendars, and emails) trigger `requires_approval = True`. The graph halts execution and sends the pending arguments to the client.
3. **Prompt Strategy**:
    - **Static Prompt**: Core HR identity and behavior rules (No hallucinations, IST time zone). Enforces that no technical backend tool names (e.g. `add_candidate`) should be leaked to the client.
    - **Dynamic Prompt**: Injected live state (Extracted Info, Active Goal, Current IST Time) and the dynamic target tool schema.
4. **Context Flattening**: Converts the `extracted_info` dict into a compact string (`- Name: Bob\n- Role: Python`). This reduces prompt tokens by ~40% compared to raw JSON.

### 2.3 `execute_node` (`execute.py`)
1. **Validation**: Checks if a tool call exists in the message.
2. **Registry Mapping**: It fetches the Python function from `tools_registry.py`.
3. **Execution**: Runs the tool with `organization` context (ensuring Alice can't see Bob's candidates).
4. **Error Handling**: If a tool fails, it returns the error string as a `ToolMessage`. The Graph then loops back to `harvey_node`, allowing the AI to "read" the error and try a different approach.

### 2.4 `summary_node` (`summary.py`)
1. **Trigger**: Activates when `len(messages) >= 8`.
2. **Aggressive Pruning**: It generates a high-level summary of the chat, stores it in `context`, and then **deletes all but the last 4 messages**.
3. **Approval State Safety**: If `requires_approval` is active, the node prevents resetting states to ensure proper WS flow.

---

## 3. View Functions

### Core Views & Middleware (`core/views.py`)

| Function / File | Description |
| :--- | :--- |
| `login_view` | Handles user authentication. Redirects users based on their role (`org_admin` -> Dashboard, `employee` -> Chat). |
| `chat_page` | Renders the main chat interface (`core.html`). Checks `has_chat_access` permission. |
| `chat_with_llm` | **API Endpoint**. Receives JSON POST requests with `prompt`. Invokes the LangGraph agent via `generate_llm_reply` and returns the response. |
| `health.py` | Admin panel view containing system health diagnostics (Redis latency, Celery worker status, environment keys). |

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
| `search_employee` | JSON API for searching employees by name/email. |
| `manage_policies` | Lists all uploaded HR policies. |
| `reindex_policy` | Manually triggers the `PolicyIndexer` to re-process a policy. |

---

## 4. Data Models (`core/models/`)

### Organization (`core/models/organization.py`)
-   **`Organization`**: The tenant. All data is siloed by this ID.
-   **`User`**: Custom user model.
    -   `role`: Determines access level (`org_admin`, `hr`, `employee`).
    -   `has_chat_access`: Controls access to the chat interface.

### Recruitment (`core/models/recruitment.py`)
-   **`Candidate`**: Represents a job applicant. Sorted by `-id` since `created_at` is absent.
    -   `skills`: JSON list of skills.
    -   `status`: 'pending', 'interviewing', 'hired', etc.
-   **`JobRole`**: Open positions.
-   **`Interview`**: Links `Candidate`, `Interviewer` (User), and `DateTime`.
-   **`EmailLog`**: Audit log of all emails sent by the agent.

### Chatbot (`core/models/chatbot.py`)
-   **`Conversation`**: A chat session. Stores `memory_state` (Redis backup).
-   **`Message`**: Individual messages for history. Content is **AES-256 encrypted** in the database.
-   **`GraphRun`**: Logs every execution of the agent, including traces of nodes visited, inputs, outputs, and errors.

---

## 5. The Tool Ecosystem & Action Confirmation

### 5.1 Shared Utility Logic (`utils.py`)
All tools depend on a shared logic layer for data normalization:
- **`resolve_user_emails`**: Checks syntax or queries User tables with multiple match options.
- **Multiple Match Handling**: Forces agent specificity if search returns >1 result.

### 5.2 Interactive Human-in-the-Loop Dialogs
When sensitive actions occur:
- **WS Communication**: `consumers.py` passes the request payload (`approve_tool`, `cancel_tool`).
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
- **`requires_approval`**: A boolean flag identifying if the current action is paused waiting for user input.
- **`context`**: A structured dictionary that acts as the "Working Memory":
- **`trace`**: A list of execution metadata (ms duration, node hits) used to power the real-time "Thinking" logs in the UI.

### 1.2 The Multi-Model Tiered Strategy & Optimization
To balance costs, latency, and reasoning depth, we employ a hybrid strategy:
- **Router (Llama-3.1-8B)**: Optimized for speed (<400ms). Used at `temp=0` to ensure deterministic intent classification. We bypass formatting instructions in favor of manual JSON parsing to keep router prompt sizes under 250 tokens.
- **Reasoner (Llama 4 Scout - 17B)**: Optimized for agentic "tool-calling" accuracy. It dynamically loads only the router's target tool schema, keeping reasoning prompt sizes under 500 tokens.
- **Summarizer (Llama-3.1-8B)**: Used for post-interaction memory compression.

---

## 2. Node-by-Node Process Logic

### 2.1 `router_node` (`router.py`)
1. **Trigger**: Every user message hits this node first.
2. **Logic**: It looks at the message syntax. If a user says "send" while an email draft exists, it force-routes to the `send_email_tool`.
3. **LLM Call**: Otherwise, it invokes the 8B model to classify intent and manually parses the JSON response.
4. **HINTS**: It generates a `target_tool` hint. This is passed to the next node to guide the reasoner.

### 2.2 `harvey_node` (`harvey.py`)
This is the central reasoning node.
1. **The LLM Bypass**: If the previous node was `execute_node`, it finds a `ToolMessage` at the end of the history. It **bypasses the LLM entirely**, returning the raw tool output. This prevents the LLM from rewriting or "explaining away" important links/IDs.
2. **Human-in-the-Loop Confirmation**: Sensitive tools (such as leaves, calendars, and emails) trigger `requires_approval = True`. The graph halts execution and sends the pending arguments to the client.
3. **Prompt Strategy**:
    - **Static Prompt**: Core HR identity and behavior rules (No hallucinations, IST time zone). Enforces that no technical backend tool names (e.g. `add_candidate`) should be leaked to the client.
    - **Dynamic Prompt**: Injected live state (Extracted Info, Active Goal, Current IST Time) and the dynamic target tool schema.
4. **Context Flattening**: Converts the `extracted_info` dict into a compact string (`- Name: Bob\n- Role: Python`). This reduces prompt tokens by ~40% compared to raw JSON.

### 2.3 `execute_node` (`execute.py`)
1. **Validation**: Checks if a tool call exists in the message.
2. **Registry Mapping**: It fetches the Python function from `tools_registry.py`.
3. **Execution**: Runs the tool with `organization` context (ensuring Alice can't see Bob's candidates).
4. **Error Handling**: If a tool fails, it returns the error string as a `ToolMessage`. The Graph then loops back to `harvey_node`, allowing the AI to "read" the error and try a different approach.

### 2.4 `summary_node` (`summary.py`)
1. **Trigger**: Activates when `len(messages) >= 8`.
2. **Aggressive Pruning**: It generates a high-level summary of the chat, stores it in `context`, and then **deletes all but the last 4 messages**.
3. **Approval State Safety**: If `requires_approval` is active, the node prevents resetting states to ensure proper WS flow.

---

## 3. View Functions

### Core Views & Middleware (`core/views.py`)

| Function / File | Description |
| :--- | :--- |
| `login_view` | Handles user authentication. Redirects users based on their role (`org_admin` -> Dashboard, `employee` -> Chat). |
| `chat_page` | Renders the main chat interface (`core.html`). Checks `has_chat_access` permission. |
| `chat_with_llm` | **API Endpoint**. Receives JSON POST requests with `prompt`. Invokes the LangGraph agent via `generate_llm_reply` and returns the response. |
| `health.py` | Admin panel view containing system health diagnostics (Redis latency, Celery worker status, environment keys). |

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
| `search_employee` | JSON API for searching employees by name/email. |
| `manage_policies` | Lists all uploaded HR policies. |
| `reindex_policy` | Manually triggers the `PolicyIndexer` to re-process a policy. |

---

## 4. Data Models (`core/models/`)

### Organization (`core/models/organization.py`)
-   **`Organization`**: The tenant. All data is siloed by this ID.
-   **`User`**: Custom user model.
    -   `role`: Determines access level (`org_admin`, `hr`, `employee`).
    -   `has_chat_access`: Controls access to the chat interface.

### Recruitment (`core/models/recruitment.py`)
-   **`Candidate`**: Represents a job applicant. Sorted by `-id` since `created_at` is absent.
    -   `skills`: JSON list of skills.
    -   `status`: 'pending', 'interviewing', 'hired', etc.
-   **`JobRole`**: Open positions.
-   **`Interview`**: Links `Candidate`, `Interviewer` (User), and `DateTime`.
-   **`EmailLog`**: Audit log of all emails sent by the agent.

### Chatbot (`core/models/chatbot.py`)
-   **`Conversation`**: A chat session. Stores `memory_state` (Redis backup).
-   **`Message`**: Individual messages for history. Content is **AES-256 encrypted** in the database.
-   **`GraphRun`**: Logs every execution of the agent, including traces of nodes visited, inputs, outputs, and errors.

---

## 5. The Tool Ecosystem & Action Confirmation

### 5.1 Shared Utility Logic (`utils.py`)
All tools depend on a shared logic layer for data normalization:
- **`resolve_user_emails`**: Checks syntax or queries User tables with multiple match options.
- **Multiple Match Handling**: Forces agent specificity if search returns >1 result.

### 5.2 Interactive Human-in-the-Loop Dialogs
When sensitive actions occur:
- **WS Communication**: `consumers.py` passes the request payload (`approve_tool`, `cancel_tool`).
- **Client Side Forms**: The UI renders edit cards dynamically. Once approved, buttons and inputs are client-side locked to prevent double submits.
- **Backend Sanitization**: `chat_service.py` contains `validate_and_sanitize_args` ensuring dates, names, durations, and email values are validated and escaped before running tool executions.

### 5.3 Offline Resume Parser Fallback
If API keys (such as `GROQ_API_KEY`) are missing, the candidate document is parsed locally in `resume_parser.py` using robust regex rules to extract name, email, and skills.

### 5.4 Google OAuth System Token Generator
Staff can trigger a system-wide Google OAuth generation flow from the Django Admin Panel home page. The view `admin_google_system_login` initiates an offline consent request, and the callback view processes the returned code to render `admin/system_token_display.html` with the generated `GOOGLE_SYSTEM_REFRESH_TOKEN` for updating `.env` files.

---

## 6. Proactive UX Architecture

To ensure the AI feels constantly engaged and helpful without burning LLM budget:
- **Token-Free Auto Greeting**: Determinisitically formats greeting packages containing time-of-day, work anniversary messages, leave action checklists, and sticky memory.
- **Copilot Action Chips**: Contextual macro chips rendered based on user permissions.
- **Celery digests**: Periodic actions running outside the request thread.

---
*Maintained by the Harvey Engineering Team*
