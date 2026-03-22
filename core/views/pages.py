from django.shortcuts import render, redirect

def landing_page(request):
    """Render the public landing page."""
    if request.user.is_authenticated:
        # Already logged in: redirect by role
        if request.user.role == "org_admin" or request.user.is_superuser:
            return redirect('admin_dashboard')
        elif getattr(request.user, "has_chat_access", False):
            return redirect('chat_view')
        else:
            return render(request, 'core/no_access.html')

    feature_categories = [
        {
            "title": "Agentic AI Engine",
            "subtitle": "Cognition & retrieval",
            "icon": "fa-brain",
            "items": [
                {"icon": "fa-project-diagram", "title": "LangGraph Intent Router", "description": "Dynamic LLM routing pipeline that classifies user intents to selectively trigger tools, RAG searches, or direct responses."},
                {"icon": "fa-database", "title": "PgVector RAG Integration", "description": "Semantic similarity searches across indexed company policies and candidate profiles using HuggingFace embeddings."},
                {"icon": "fa-comment-dots", "title": "Contextual Memory Streams", "description": "Session-aware database storage maintaining deep conversational context across heavily branching chat threads."},
                {"icon": "fa-magic", "title": "Automated Action Mutations", "description": "Securely granted AI permissions to automatically create job postings, candidates, and leave requests via chat."}
            ]
        },
        {
            "title": "Asynchronous Backend",
            "subtitle": "Concurrency & streaming",
            "icon": "fa-bolt",
            "items": [
                {"icon": "fa-broadcast-tower", "title": "Django Channels WebSockets", "description": "Real-time WebSocket streaming for fast AI token generation and instant, responsive frontend UI updates."},
                {"icon": "fa-layer-group", "title": "Celery & Redis Queues", "description": "Distributed asynchronous job queues handling heavy background tasks, email dispatch, and document OCR."},
                {"icon": "fa-code-branch", "title": "Complex Django ORM", "description": "Advanced queryset optimizations using select_related, custom managers, and efficient JSONField processing."},
                {"icon": "fab fa-markdown", "title": "Dynamic AST Hydration", "description": "Vanilla JS parsing incoming server markdown streams into formatted HTML via custom AST processing."}
            ]
        },
        {
            "title": "Proactive Agentic UX",
            "subtitle": "Zero-token logic & anticipation",
            "icon": "fa-lightbulb",
            "items": [
                {"icon": "fa-comment-medical", "title": "Zero-Token Auto-Greetings", "description": "Deterministically evaluates server time, sticky session context, and worker anniversaries to inject instant, context-aware greetings before the LLM fires."},
                {"icon": "fa-calendar-check", "title": "Dashboard Alert Cards", "description": "Glowing UI cards that continuously scan SQL databases via ORM to highlight pending manager tasks right upon login."},
                {"icon": "fa-mouse-pointer", "title": "Copilot Action Chips", "description": "Context-sensitive macro buttons mapped uniquely to roles (e.g. 'Apply for PTO' for employees) that pre-fill strict prompts into WebSockets."},
                {"icon": "fa-envelope-open-text", "title": "Scalable Celery Digests", "description": "Automated background workers aggregating user statuses to dispatch customized, OAuth-secured Gmail summary reports."}
            ]
        },
        {
            "title": "Modern Architecture",
            "subtitle": "Security & infrastructure",
            "icon": "fa-server",
            "items": [
                {"icon": "fab fa-docker", "title": "Dockerized Infrastructure", "description": "Fully containerized environments ensuring strict parity across Postgres DBs, Redis cache, and ASGI application servers."},
                {"icon": "fa-building", "title": "Multi-Tenancy & RBAC", "description": "Data segregation by Organization ID enforcing isolated workspaces and robust Role-Based Access Control boundaries."},
                {"icon": "fab fa-google", "title": "Google Identity OAuth", "description": "Secure enterprise OAuth 2.0 flow integrated seamlessly alongside custom cryptographic invite mechanics."},
                {"icon": "fa-plug", "title": "HRMS API Connectors", "description": "Custom webhook endpoints mimicking bi-directional sync operations with BambooHR and Rippling systems."}
            ]
        },
        {
            "title": 'Data Privacy <span class="text-rose-400">&</span> Security',
            "subtitle": "Protection & compliance",
            "icon": "fa-shield-alt",
            "items": [
                {"icon": "fa-lock", "title": "End-to-End Encryption", "description": "Sensitive candidate data and HRMS API keys are encrypted at rest using Fernet symmetric encryption algorithms."},
                {"icon": "fa-key", "title": "Cryptographic Tokens", "description": "Time-sensitive, cryptographically signed invite tokens prevent unauthorized access and replay attacks during onboarding."},
                {"icon": "fa-user-shield", "title": "LLM Prompt Sanitization", "description": "Injecting system-level prompt guards to heavily restrict the AI from leaking proprietary organization data between contexts."},
                {"icon": "fa-server", "title": "Strict Tenant Isolation", "description": "Middleware and queryset scoping guarantees that vector embeddings and company policies are strictly sandboxed per organization."}
            ]
        }
    ]

    return render(request, "core/landing_page.html", {"feature_categories": feature_categories})
