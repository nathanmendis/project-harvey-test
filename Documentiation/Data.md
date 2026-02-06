# Data Architecture & Schema Reference

This document provides a comprehensive overview of the data layer in Project Harvey, including the relational schema (DDL), Entity Relationship (ER) diagram, and UML Class diagrams.

---

## 1. Data Flow Diagrams (DFD)

### 1.1 Level 0: Context Diagram
The high-level interaction between the user, the system, and external entities.

```mermaid
graph LR
    User((User)) -- "Text Prompt" --> Harvey[("Project Harvey System")]
    Harvey -- "AI Response / UI Update" --> User
    
    Harvey -- "OAuth / API Call" --> Google[("Google Workspace")]
    Google -- "Token / Action Status" --> Harvey
    
    Source[("File/URL Source")] -- "Raw Content" --> Harvey
```

### 1.2 Level 1: System Data Flow
A detailed view of how data flows through the internal AI and integration layers.

```mermaid
graph TD
    User((User)) -- "1. Prompt (WS)" --> WS[("WebSocket Entry")]
    WS -- "2. Event Frame" --> Redis((Redis Bus))
    
    subgraph AI_Core [The Brain]
        Redis -- "3. State Trigger" --> Router[("Process 1.0: Router (8B)")]
        Router -- "4. Intent + HINT" --> Reasoner[("Process 2.0: Reasoner (17B)")]
        Reasoner -- "5. Tool Call JSON" --> Exec[("Process 3.0: Execution Engine")]
        
        Exec -- "6. Search Key" --> PGV[(Data Store: PGVector)]
        PGV -- "7. Result" --> Exec
        
        Exec -- "8. DB Operation" --> DB[(Data Store: Postgres)]
        DB -- "9. Confirmation" --> Exec
        
        Exec -- "10. Tool Result" --> Reasoner
    end
    
    Reasoner -- "11. streaming Trace" --> Redis
    Reasoner -- "12. Final Response" --> Redis
    
    Redis -- "13. JSON Frame" --> WS
    WS -- "14. UI Bubble" --> User
```

---

## 2. Entity Relationship (ER) Diagram
This diagram visualizes the relationships between the core entities: Organizations, Users, Candidates, and the AI Conversation state.

```mermaid
erDiagram
    ORGANIZATION ||--o{ USER : contains
    ORGANIZATION ||--o{ CANDIDATE : manages
    ORGANIZATION ||--o{ JOB_ROLE : defines
    ORGANIZATION ||--o{ CONVERSATION : owns
    ORGANIZATION ||--o{ POLICY : hosts
    
    USER ||--o{ CONVERSATION : participates
    USER ||--o{ INTERVIEW : conducts
    USER ||--o{ LEAVE_REQUEST : submits
    
    CONVERSATION ||--o{ MESSAGE : contains
    CONVERSATION ||--o{ GRAPH_RUN : tracks
    
    CANDIDATE ||--o{ INTERVIEW : undergoes
    CANDIDATE ||--o{ CANDIDATE_JOB_SCORE : evaluated_in
    JOB_ROLE ||--o{ CANDIDATE_JOB_SCORE : matches
    
    POLICY ||--o{ POLICY_CHUNK : split_into
```

---

## 2. UML Class Diagram
A detailed view of the model properties and behavioral methods.

```mermaid
classDiagram
    class Organization {
        +String org_id
        +String name
        +String domain
        +String google_refresh_token
        +DateTime google_token_expires
        +String google_connected_email
    }

    class User {
        +String username
        +String name
        +String role
        +Boolean has_chat_access
        +is_org_admin()
    }

    class Candidate {
        +String name
        +String email
        +JSON skills
        +File resume_file
        +String status
    }

    class JobRole {
        +String title
        +String description
        +String requirements
        +String department
    }

    class Conversation {
        +String title
        +JSON context_state
        +JSON memory_state
    }

    class Message {
        +String sender
        +String message_text
        +String text
        +save()
    }

    class Policy {
        +String title
        +String source_type
        +String status
    }

    class GraphRun {
        +UUID id
        +String status
        +JSON trace
        +DateTime started_at
    }

    Organization "1" *-- "many" User
    Organization "1" *-- "many" Candidate
    User "1" -- "many" Conversation
    Conversation "1" *-- "many" Message
    Candidate "many" -- "many" JobRole : Scored
```

---

## 3. Data Definition Language (DDL)
Below is the high-level schema for the primary tables as represented in Postgres.

### 3.1 Core Identity & Multi-Tenancy
```sql
CREATE TABLE core_organization (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(100) UNIQUE,
    google_refresh_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE core_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'employee',
    organization_id INTEGER REFERENCES core_organization(id),
    has_chat_access BOOLEAN DEFAULT TRUE
);
```

### 3.2 Recruitment & Pipeline
```sql
CREATE TABLE core_candidate (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES core_organization(id),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    skills JSONB,
    status VARCHAR(50) DEFAULT 'pending'
);

CREATE TABLE core_jobrole (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES core_organization(id),
    title VARCHAR(255) NOT NULL,
    department VARCHAR(255)
);

CREATE TABLE core_interview (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES core_organization(id),
    candidate_id INTEGER REFERENCES core_candidate(id),
    interviewer_id INTEGER REFERENCES core_user(id),
    date_time TIMESTAMP NOT NULL
);
```

### 3.3 AI & Audit (LangGraph)
```sql
CREATE TABLE core_conversation (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES core_user(id),
    context_state JSONB,
    memory_state JSONB
);

CREATE TABLE core_message (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES core_conversation(id),
    sender VARCHAR(10) NOT NULL,
    message_text TEXT NOT NULL -- Encrypted: enc:<payload>
);

CREATE TABLE core_graphrun (
    id UUID PRIMARY KEY,
    conversation_id INTEGER REFERENCES core_conversation(id),
    trace JSONB,
    status VARCHAR(20)
);
```

### 3.4 Vector Search (PGVector)
```sql
CREATE TABLE core_policychunk (
    id SERIAL PRIMARY KEY,
    policy_id UUID REFERENCES core_policy(id),
    text TEXT,
    vector_id VARCHAR(100), -- Linked to PGVector Index
    metadata JSONB
);
```
