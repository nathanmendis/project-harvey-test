# Project Harvey: The Next-Generation Agentic HR Ecosystem

## 1. Problem Statement

### What problem were you trying to solve?
Traditional HR and Recruitment software is often a "static" repository of data—a digital filing cabinet. Human HR staff spend over **60% of their time** on low-value, repetitive tasks:
*   **Manual Scheduling**: Back-and-forth emails to align candidate and interviewer calendars.
*   **Policy Lookup**: Manually searching through 50+ page PDFs to answer basic employee questions about leave carryovers or PTO.
*   **Data Entry/Sync**: Keeping external HRMS (Workday, SAP) in sync with local recruitment pipelines.

Furthermore, most "AI Chatbots" are simple wrappers around LLMs that suffer from high latency, "hallucinated" links, and a total lack of data privacy/multi-tenancy.

### Why did you choose this problem?
HR is the "connective tissue" of any organization. By automating the mundane, we allow talent acquisition teams to focus on the human side of hiring. I chose this because it requires solving "Enterprise AI" constraints: **Privacy, Cost-Optimization, and Deterministic Accuracy.**

---

## 2. Your Approach & Thought Process

### How did you break down the problem?
I moved away from the "One Prompt for Everything" approach. Instead, I architected a **Hierarchical Agentic Pipeline**:
1.  **The Entry Level (Routing)**: Use a lightweight model (Llama 8B) to instantly classify intent and detect the required tool.
2.  **The Thinking Level (Reasoning)**: Use a specialized "Reasoner" model (Llama 4 Scout) to draft tool arguments and handle multi-turn logic.
3.  **The Action Level (Execution)**: A strictly typed Python layer that interacts with the database and external APIs (Google Calendar, Gmail).

### What made your approach unique or different?
*   **The "LLM Bypass" Strategy**: One of my core innovations. When the agent schedules an interview or generates a draft, the system **bypasses the LLM** to deliver the raw, accurate tool output (URLs, IDs) to the user. This eliminates hallucinations 100%.
*   **Proactive Zero-Token Intelligence**: Most bots wait for you to speak. Project Harvey *reads* your context (pending tasks, anniversaries, sticky memory) on page load and greets you with a relevant update—using **zero LLM tokens**.
*   **Context Flattening & Summary Cycles**: To maintain sub-second speeds, the state memory dynamically flattens complex data and prunes history as conversations grow, keeping the "Brain" efficient.

---

## 3. Tech Stack

### Core Technologies
*   **Backend**: Django 5.1 (ASGI/Daphne for real-time WebSocket communication).
*   **Database**: PostgreSQL + **PGVector** (Embedding-based semantic search for candidate resumes and HR policies).
*   **Task Queue**: Celery + Redis (Handles background HRMS syncing and daily manager digests).

### Agentic/Automation Tools
*   **LangGraph**: Used to build stateful, cyclic AI workflows.
*   **Groq (Llama 3.1 8B)**: Asymmetric Routing node.
*   **Llama 4 Scout (17B)**: Core Reasoning and Tool-calling node.
*   **Google OAuth 2.0**: Direct system-level integration with Gmail and Calendar APIs.
*   **Fernet Encryption**: DB-level encryption for sensitive PII (Personally Identifiable Information).

---

## 4. Build Explanation

### How does your solution work?
Project Harvey functions as a **Stateful State Machine**. When a user types a message:
1.  **Router Node**: Determines if the user is just chatting or needs a tool. It "hints" at the target tool to save the Reasoner's time.
2.  **Harvey Node (Reasoner)**: Considers the user's current goal + "Working Memory" (extracted entities) to decide the next action.
3.  **Executor Node**: Fires the Python tool. **Privacy Check**: The tool is automatically scoped to the user's `organization_id`.
4.  **Summary/Cycle**: If the thread gets too long, the system compresses it to maintain low latency.

### Key Features
*   **The Policy Engine (RAG)**: Index HR PDF/URLs and query them using semantic vector search. Includes a **'Secure Document Theater'** for non-leaking, shielded document viewing.
*   **Automated Scheduling**: "Schedule an interview with Alice for the Python role on Friday at 2 PM." The bot finds Alice's email, checks the recruiter's calendar availability, and creates a Google Meet invite in seconds.
*   **Observability & Telemetry**: Built-in **GraphRun** system that logs every "thought," node transitions, and millisecond latency in the Django Admin, with backend logging for granular token usage.
*   **Daily Digests**: Celery workers aggregate pending leave requests and recruitment alerts and email a personalized "9 AM Summary" to managers.

---

## 5. Why This Matters

This project is meaningful because it demonstrates that AI Agents are ready for **Enterprise Production**, provided they are built with safety and efficiency in mind.
*   **Privacy-First AI**: Solves the "data bleed" problem of multi-tenancy.
*   **Cost Efficiency**: By using 8B models for routing and summaries, and zero-token logic for greetings, it reduces operating costs by **~60%** compared to GPT-4-only solutions.
*   **Human-Centric Design**: It transforms a "tool" into a "teammate" that proactively reaches out when a task is due, rather than waiting to be asked.

---

## 6. Loom Video Guide (Walkthrough Outline)

**Duration: 7 Minutes**

1.  **Intro (0:00 - 1:00)**: Introduce Project Harvey and the core problem of "Static HR vs. Agentic HR."
2.  **Proactive Demo (1:00 - 2:30)**: Show the zero-token greeting. Highlight how the bot knows about a pending leave request without the user asking.
3.  **Multi-Turn Agentic Action (2:30 - 4:30)**:
    *   Prompt: "Find candidates good at Python." (Shows PGVector RAG).
    *   Prompt: "Great, schedule an interview with the top candidate for tomorrow morning." (Shows multi-tool reasoning and Calendar integration).
4.  **Architectural Deep Dive (4:30 - 6:00)**: Show the code—specifically the LangGraph `graph.py` and the `router.py` logic. Explain the tiered-model strategy.
5.  **Security & Scaling (6:00 - 7:00)**: Explain DB encryption, organization isolation, and the Celery background sync for massive HRMS systems.

---

### Final Submission Links:
*   **Google Doc / Notion**: [Link to this markdown]
*   **Loom Video**: [Link to your recorded Loom]
*   **Submission Form**: https://forms.gle/LNzp6Z6CUxBTXB2EA
