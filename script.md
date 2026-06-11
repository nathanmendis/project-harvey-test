# Project Harvey: Loom Video Script (7 Minutes)

### 0:00 - 1:00 | The Introduction
*(Scene: Show the browser with the login screen or dashboard)*
"Hi everyone! I’m [Your Name], and today I’m excited to show you **Project Harvey**. 

Harvey isn't just another HR dashboard—it’s an **Agentic HR Ecosystem**. Most HR tools are static databases where you have to do all the work. Harvey reverses that. It’s a proactive teammate that handles the high-friction parts of recruitment and policy management so you can focus on people, not paperwork."

### 1:00 - 2:30 | Proactive Intelligence (The "Wow" Moment)
*(Scene: Log in and show the Dashboard with the chat interface)*
"Let's look at the first agentic feature: **Proactive Intelligence**. 

Notice the greeting here. Without me typing a single word, Harvey has already scanned the database. It knows I have two pending leave requests to approve and that there’s a work anniversary today. 

Crucially, this uses **zero LLM tokens**. I built a deterministic logic layer that feeds this state directly into the interface on page load. It feels like the AI is always 'awake' and aware of the business context before I even open my mouth."

### 2:30 - 4:30 | The Agentic Workflow in Action
*(Scene: Focus on the Chat Input)*
"Now, let’s see a complex multi-turn workflow. I’m going to give a broad goal: 
*Type: 'Find me Python experts in our candidate pool and schedule an interview with the best one for tomorrow afternoon.'*

Watch the 'Thinking' logs. Harvey is now:
1.  **Routing**: Identifying that I need recruitment tools.
2.  **Searching**: Querying our **PGVector** index to find the most relevant resumes.
3.  **Reasoning**: It sees 'Alice' is the top candidate but checks my calendar first. 
*Point out:* "Notice how it handles the **Organization Timezone** automatically—whether I'm in NYC or Bangalore, the API syncs the offset deterministically."
4.  **Executing**: It’s hitting the Google Calendar API and Google Meet API simultaneously.

And there it is. A generated meeting link, a calendar invite sent, and a confirmation to the candidate. What would normally take a recruiter 15 minutes of tab-switching happened in seconds through a single goal-based prompt."

### 4:30 - 6:00 | The "Brain" (The Technical Layer)
*(Scene: Switch to VS Code. Show d:/Code/project_harvey/project-harvey-test/core/ai/agentic/graph/graph.py)*
"Under the hood, this is powered by **LangGraph**. I chose a stateful, cyclic architecture because recruitment isn't linear. 

*Highlight:* "I’ve also implemented a proprietary **Telemetry System** called **GraphRun**. If we go to the admin panel, we can see the full trace of every node visited and the exact millisecond latency for each transition. Our backend analytics also capture granular token usage per model, ensuring we can monitor costs and optimize performance at scale."

I use a **Tiered Model Strategy**:
*   **Llama 3.1 8B** acts as our 'Router.' It’s lightning-fast and only classifies intent.
*   **Llama 4 Scout** acts as our 'Reasoner.' It’s specialized for handling tool-calling and JSON schemas.

By splitting these tasks, I’ve reduced API latency by 80% and minimized costs while maintaining enterprise-grade accuracy. I also implemented an **'LLM Bypass'**. When a tool returns a URL or a UUID, we bypass the LLM for the final delivery to ensure there’s zero chance of 'hallucination' in critical links."

### 6:00 - 7:00 | Security & Conclusion
*(Scene: Show the Admin Panel/Policy section)*
"Finally, security. Harvey is a multi-tenant SaaS. Beyond simple RBAC, I’ve implemented what I call the **'Secure Document Theater'**. When a policy is found via RAG, it's rendered in a shielded mode that prevents document leakage and prevents third-party scraping. 

We also use **Fernet Encryption** for all PII data. Project Harvey demonstrates that AI agents aren't just for chat; they're the next generation of enterprise middleware. Thanks for watching!"
