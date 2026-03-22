# Project Harvey: Developer Problem-Solving & Architectural Decisions

Throughout the lifecycle of Project Harvey v3.1, a variety of critical scaling, security, and logic problems were solved through proactive developer expertise. Below is a formalized list of the most critical interventions that guarantee the system's resilience and enterprise readiness.

---

## 1. Preventing Synchronous Server Timeouts (Celery vs. HTTP Threads)
* **The Problem:** In multiple areas of the project (e.g., HRMS Batch Syncs, RAG Indexing, Mass-Provisioning Leave Policies), processing thousands of records synchronously inside an HTTP request would block the ASGI server thread, causing web requests to hang or time out.
* **The Expertise & Solution:** Transitioned heavy `O(N)` tasks out of Django views and `post_save` signals. Implemented highly decoupled, asynchronous **Celery workers** backed by Redis. This offloaded heavy lifting (like looping through 10,000 employees to create `LeaveBalance` objects or executing `ModelIndexer()`) into background queues securely triggered via `transaction.on_commit()`, keeping API latencies sub-second.

## 2. Nullifying Multi-Tenant Data Leakage
* **The Problem:** A multi-tenant SaaS application inherently faces the risk of one company's HR admin executing a search tool that accidentally parses through resumes belonging to a completely different company.
* **The Expertise & Solution:** Implemented strict DB-level enforcement. Every single data model (`Candidate`, `JobRole`, `Interview`, `Conversation`, `OrganizationLeavePolicy`) is hard-linked with an `organization` ForeignKey. The Agentic Graph fundamentally injects the `organization_id` of the requesting user into every tool invocation. It is impossible for the LangGraph tools to break this boundary.

## 3. Resolving Token Limit Exhaustion & "Context Bloat"
* **The Problem:** In long-running conversations, standard LangChain/Prompting techniques pass the entire multi-turn JSON history to the LLM. This rapidly exhausts maximum token limits (e.g., hitting 8k/16k caps) and degrades response times, heavily increasing API costs.
* **The Expertise & Solution:** Architected a **"Context Flattening"** and **Aggressive Pruning** strategy inside the custom LangGraph state memory constraints.
  1. The `harvey_node` dynamically flattens complex nested JSON arrays into bulleted raw strings, saving up to 40% in token usage per interaction.
  2. The `summary_node` observes the thread length; once it exceeds 8 turns, it forcibly compresses the conversation into a high-level summary and prunes the stack down to heavily optimize memory retention.

## 4. LLM "Hallucination" and Tool Output Corruption
* **The Problem:** When an LLM executes a tool (e.g., "Schedule an interview and get the Google Meet link") and then reads the tool's raw output, it attempts to naturally re-phrase the output for the user. It will frequently warp Google Meet URLs, change UUIDs, or hallucinate meeting times.
* **The Expertise & Solution:** Developed a highly customized **"LLM Bypass"** logic state in the LangGraph reasoner. When the previous node is an `execute_node` generating strict functional output (like calendar links or email drafts), the agent bypasses sending that output back to the LLM entirely, passing the pristine, untampered tool response directly to the user's socket connection.

## 5. Defense-in-Depth for Sensitive AI Actions
* **The Problem:** An AI agent capable of scheduling calendars, syncing external HRMS tools, or changing Leave Policies presents a massive security vector if a malicious user prompts it directly.
* **The Expertise & Solution:** 
  1. Decoupled Identity systems: User OAuth is strictly separated from the System's Backend Action OAuth. The bot acts autonomously on the backend without giving users direct API keys.
  2. **Token-Gated UI Configs:** Developed a highly secure backend flow where admins must go directly to the core Django Superuser Panel to generate time-expiring, single-use `edit_tokens` simply to *unlock* the HRMS and Leave setting dashboards. 

## 6. Real-Time Distributed Logging for AI Latency Monitoring
* **The Problem:** Tracing exactly which node is slowing down (Router vs. Summary vs. Tool Execution) is nearly impossible in asynchronous LangGraph flows without dedicated APM systems.
* **The Expertise & Solution:** Developed a proprietary `GraphRun` persistence model. Every interaction saves an immutable JSON record of the absolute trace. It tracks the exact millisecond latency per node, the prompt-to-completion token counts, and the precise inputs. This provides granular, actionable developer telemetry directly inside the Django admin panel.

## 7. Dynamic Geographic Timezone Handling
* **The Problem:** A simple `datetime.now()` command relies on the host server's local time, completely ruining the calendar tool when a recruiter in New York attempts to schedule an interview for candidates in Tokyo.
* **The Expertise & Solution:** Integrated dynamic fallback Timezone injection native to the `Organization` mapping. Tools programmatically look up the specific tenant's timezone, align `pytz`/`zoneinfo`, and strictly serialize ISO formats before hitting the Google Calendar API, eliminating drift.

## 8. Graceful Fallbacks for Ambiguous Tool Execution
* **The Problem:** If a user asked the AI to "email Alex," but the DB contained `Alex Smith` and `Alex Doe`, the LLM would arbitrarily guess which one to email, resulting in severe privacy breaches.
* **The Expertise & Solution:** Configured the `resolve_user_emails` utility to perform deterministic "Multiple Match Detection". If the regex + ORM query yields >1 match, the tool immediately halts execution and returns an error strictly demanding the LLM prompt the user for clarification before proceeding to draft the email.
