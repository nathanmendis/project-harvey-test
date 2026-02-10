# HR Integration Architecture - Visual Diagrams

This document contains detailed visual diagrams for the HR system integration architecture, with a focus on **Pattern B: Scheduled Batch Sync** - the recommended production approach.

---

## Pattern B: Scheduled Batch Sync Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "External HRMS Systems"
        HRMS1[Workday API]
        HRMS2[BambooHR API]
        HRMS3[SAP SuccessFactors API]
        HRMS4[Custom HRMS API]
    end

    subgraph "Harvey Integration Layer"
        SCHEDULER[Celery Beat Scheduler<br/>⏰ Triggers every 2 hours]
        QUEUE[Task Queue<br/>Redis]

        subgraph "Sync Workers"
            WORKER1[Employee Sync Task]
            WORKER2[Candidate Sync Task]
            WORKER3[Interview Sync Task]
            WORKER4[Leave Sync Task]
        end

        ADAPTER[HRMS Adapter Registry]
        TRANSFORMER[Data Transformer<br/>HRMS → Harvey Format]
        TRACKER[Sync Status Tracker<br/>Redis Cache]
    end

    subgraph "Harvey Database"
        DB[(PostgreSQL<br/>Local Data Copy)]
        CACHE[(Redis<br/>Sync Status)]
    end

    subgraph "Harvey Application"
        TOOLS[Harvey AI Tools]
        API[Harvey API]
        ADMIN[Admin Dashboard]
    end

    SCHEDULER -->|Triggers| QUEUE
    QUEUE --> WORKER1 & WORKER2 & WORKER3 & WORKER4
    WORKER1 & WORKER2 & WORKER3 & WORKER4 --> ADAPTER
    ADAPTER -->|Fetch Data| HRMS1 & HRMS2 & HRMS3 & HRMS4
    ADAPTER --> TRANSFORMER
    TRANSFORMER -->|Bulk Insert/Update| DB
    WORKER1 & WORKER2 & WORKER3 & WORKER4 --> TRACKER
    TRACKER --> CACHE

    TOOLS & API -->|Query Local Data| DB
    ADMIN -->|Monitor Sync| CACHE

    style SCHEDULER fill:#4CAF50,stroke:#2E7D32,color:#fff
    style DB fill:#2196F3,stroke:#1565C0,color:#fff
    style CACHE fill:#FF9800,stroke:#E65100,color:#fff
    style TRANSFORMER fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

---

## Detailed Sync Workflow

### Employee Sync Process

```mermaid
sequenceDiagram
    participant CB as Celery Beat
    participant Q as Task Queue
    participant ST as Sync Task
    participant T as Tracker
    participant A as HRMS Adapter
    participant H as External HRMS
    participant DT as Data Transformer
    participant DB as PostgreSQL
    participant R as Redis Cache

    Note over CB: Every 2 hours
    CB->>Q: Trigger sync_all_employees
    Q->>ST: Execute sync task

    ST->>T: start_sync(org_id, 'employees')
    T->>R: Store sync_id, status='running'
    T-->>ST: Return sync_id

    ST->>T: get_last_sync_time()
    T->>R: Fetch last successful sync
    T-->>ST: Return timestamp

    loop For each page
        ST->>A: get_employees(page, page_size=100)
        A->>H: GET /api/v1/employees?page=1
        H-->>A: Return employee data
        A-->>ST: Return employees list

        loop For each employee
            alt Employee updated after last_sync
                ST->>DT: transform(employee_data)
                DT-->>ST: Harvey format data
                ST->>DB: update_or_create(employee)
                DB-->>ST: Success
            else Skip unchanged
                Note over ST: Skip (incremental sync)
            end
        end
    end

    ST->>T: complete_sync(sync_id, count)
    T->>R: Update status='completed'
    T->>R: Update last_sync_time

    Note over ST,R: Sync completed successfully
```

---

## Sync Task State Machine

```mermaid
stateDiagram-v2
    [*] --> Scheduled: Celery Beat Trigger

    Scheduled --> Running: Task Started
    Running --> FetchingData: Get HRMS Adapter

    FetchingData --> TransformingData: API Call Success
    FetchingData --> RetryLogic: API Call Failed

    TransformingData --> SavingData: Data Transformed
    SavingData --> CheckingPages: Batch Saved

    CheckingPages --> FetchingData: More Pages Exist
    CheckingPages --> Completed: All Pages Processed

    RetryLogic --> FetchingData: Retry (Attempt 1-3)
    RetryLogic --> Failed: Max Retries Exceeded

    Completed --> [*]: Update Sync Status
    Failed --> DeadLetterQueue: Send to DLQ
    DeadLetterQueue --> [*]: Admin Notified

    note right of Running
        Sync ID generated
        Status tracked in Redis
    end note

    note right of FetchingData
        Incremental sync:
        Only fetch records
        updated after last_sync
    end note

    note right of SavingData
        Bulk operations:
        update_or_create
        Transaction handling
    end note
```

---

## Data Flow Architecture

```mermaid
graph LR
    subgraph "1. Scheduling"
        A[Celery Beat<br/>Cron Schedule]
    end

    subgraph "2. Task Execution"
        B[Sync Task<br/>Celery Worker]
        C[Sync Tracker<br/>Redis]
    end

    subgraph "3. Data Fetching"
        D[HRMS Adapter]
        E[External HRMS API]
        F{Incremental<br/>Sync Check}
    end

    subgraph "4. Data Processing"
        G[Data Transformer]
        H[Validation]
        I[Field Mapping]
    end

    subgraph "5. Data Storage"
        J[(PostgreSQL)]
        K[Bulk Insert/Update]
    end

    subgraph "6. Monitoring"
        L[Admin Dashboard]
        M[Sync Status]
        N[Error Logs]
    end

    A -->|Trigger| B
    B -->|Track| C
    B --> D
    D -->|API Call| E
    E -->|Response| F
    F -->|Changed Records| G
    F -->|Skip| C
    G --> H
    H --> I
    I --> K
    K --> J
    B -->|Update Status| C
    C --> M
    B -->|Log Errors| N
    L --> M
    L --> N

    style A fill:#4CAF50,stroke:#2E7D32,color:#fff
    style J fill:#2196F3,stroke:#1565C0,color:#fff
    style C fill:#FF9800,stroke:#E65100,color:#fff
    style L fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

---

## Sync Frequency Strategy

```mermaid
gantt
    title HR Data Sync Schedule (Pattern B)
    dateFormat HH:mm
    axisFormat %H:%M

    section Employees
    Sync Every 2 Hours    :active, emp1, 00:00, 2h
    Sync Every 2 Hours    :active, emp2, 02:00, 2h
    Sync Every 2 Hours    :active, emp3, 04:00, 2h
    Sync Every 2 Hours    :active, emp4, 06:00, 2h

    section Candidates
    Sync Every Hour       :crit, cand1, 00:00, 1h
    Sync Every Hour       :crit, cand2, 01:00, 1h
    Sync Every Hour       :crit, cand3, 02:00, 1h
    Sync Every Hour       :crit, cand4, 03:00, 1h

    section Interviews
    Sync Every 30 Min     :done, int1, 00:00, 30m
    Sync Every 30 Min     :done, int2, 00:30, 30m
    Sync Every 30 Min     :done, int3, 01:00, 30m
    Sync Every 30 Min     :done, int4, 01:30, 30m

    section Leave Requests
    Daily at 1 AM         :milestone, leave1, 01:00, 0m
```

---

## Error Handling Flow

```mermaid
graph TD
    START[Sync Task Execution] --> TRY{Try Sync}

    TRY -->|Success| TRANSFORM[Transform Data]
    TRY -->|API Error| CATCH[Catch Exception]
    TRY -->|Network Error| CATCH
    TRY -->|Timeout| CATCH

    TRANSFORM --> SAVE[Save to Database]
    SAVE -->|Success| COMPLETE[Complete Sync]
    SAVE -->|DB Error| CATCH

    CATCH --> LOG[Log Error Details]
    LOG --> RETRY{Retry Count < 3?}

    RETRY -->|Yes| BACKOFF[Exponential Backoff<br/>Wait 5, 10, 20 min]
    BACKOFF --> TRY

    RETRY -->|No| FAIL[Mark Sync Failed]
    FAIL --> DLQ[Dead Letter Queue]
    DLQ --> NOTIFY[Notify Admin]
    NOTIFY --> END[End]

    COMPLETE --> UPDATE[Update Sync Status]
    UPDATE --> CACHE[Cache Last Sync Time]
    CACHE --> END

    style START fill:#4CAF50,stroke:#2E7D32,color:#fff
    style COMPLETE fill:#4CAF50,stroke:#2E7D32,color:#fff
    style CATCH fill:#F44336,stroke:#C62828,color:#fff
    style FAIL fill:#F44336,stroke:#C62828,color:#fff
    style RETRY fill:#FF9800,stroke:#E65100,color:#fff
```

---

## Pattern Comparison

```mermaid
graph TB
    subgraph "Pattern A: Real-time Sync"
        A1[Harvey Request] --> A2[Query HRMS API]
        A2 --> A3[Wait for Response]
        A3 --> A4[Return to User]
        A5[❌ High Latency<br/>❌ API Dependency<br/>❌ Higher Costs]
    end

    subgraph "Pattern B: Batch Sync ⭐"
        B1[Harvey Request] --> B2[Query Local DB]
        B2 --> B3[Instant Response]
        B4[Background: Celery] -.->|Periodic Sync| B5[Update Local DB]
        B6[✅ Sub-second Response<br/>✅ Offline Capable<br/>✅ Cost Effective<br/>✅ Data Sovereignty]
    end

    subgraph "Pattern C: Webhook Sync"
        C1[HRMS Event] --> C2[Webhook to Harvey]
        C2 --> C3[Update Local DB]
        C4[Harvey Request] --> C5[Query Local DB]
        C6[⚠️ Requires HRMS Support<br/>✅ Near Real-time<br/>⚠️ Complex Setup]
    end

    style B1 fill:#4CAF50,stroke:#2E7D32,color:#fff
    style B2 fill:#4CAF50,stroke:#2E7D32,color:#fff
    style B3 fill:#4CAF50,stroke:#2E7D32,color:#fff
    style B6 fill:#E8F5E9,stroke:#4CAF50,color:#000
```

---

## Production Deployment Architecture

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/HAProxy]
    end

    subgraph "Harvey Application Servers"
        APP1[Harvey App 1<br/>Daphne]
        APP2[Harvey App 2<br/>Daphne]
        APP3[Harvey App 3<br/>Daphne]
    end

    subgraph "Background Workers"
        BEAT[Celery Beat<br/>Scheduler]
        W1[Celery Worker 1<br/>Employee Sync]
        W2[Celery Worker 2<br/>Candidate Sync]
        W3[Celery Worker 3<br/>Interview Sync]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Primary)]
        PG_R[(PostgreSQL<br/>Read Replica)]
        REDIS[(Redis<br/>Cache & Queue)]
    end

    subgraph "External Services"
        HRMS[External HRMS<br/>Workday/BambooHR]
        MONITOR[Monitoring<br/>Prometheus/Grafana]
    end

    LB --> APP1 & APP2 & APP3
    APP1 & APP2 & APP3 -->|Read| PG_R
    APP1 & APP2 & APP3 -->|Write| PG

    BEAT -->|Schedule| REDIS
    REDIS --> W1 & W2 & W3
    W1 & W2 & W3 -->|Fetch Data| HRMS
    W1 & W2 & W3 -->|Write| PG
    W1 & W2 & W3 -->|Track Status| REDIS

    PG -.->|Replicate| PG_R

    APP1 & APP2 & APP3 --> MONITOR
    W1 & W2 & W3 --> MONITOR

    style BEAT fill:#4CAF50,stroke:#2E7D32,color:#fff
    style PG fill:#2196F3,stroke:#1565C0,color:#fff
    style REDIS fill:#FF9800,stroke:#E65100,color:#fff
    style HRMS fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

---

## Key Benefits of Pattern B

### Performance Comparison

| Metric                 | Pattern A (Real-time) | Pattern B (Batch) ⭐ | Pattern C (Webhook) |
| ---------------------- | --------------------- | -------------------- | ------------------- |
| **Query Latency**      | 500-2000ms            | <50ms                | <50ms               |
| **Offline Capability** | ❌ No                 | ✅ Yes               | ✅ Yes              |
| **API Calls/Day**      | 10,000+               | 50-100               | Event-based         |
| **Data Freshness**     | Real-time             | 30min - 2hr          | Near real-time      |
| **Setup Complexity**   | Low                   | Medium               | High                |
| **HRMS Dependency**    | High                  | Low                  | Medium              |
| **Cost**               | High                  | Low                  | Medium              |
| **Production Ready**   | ⚠️ Demo Only          | ✅ Recommended       | ⚠️ If Supported     |

### Security & Compliance

```mermaid
mindmap
  root((Pattern B<br/>Benefits))
    Data Sovereignty
      Full control over data
      Local storage
      No external dependencies
    Compliance
      GDPR compliant
      Audit trail
      Data retention policies
      Encryption at rest
    Security
      Reduced attack surface
      Fewer external connections
      API rate limiting
      Credential encryption
    Performance
      Sub-second queries
      No API latency
      Bulk operations
      Database indexing
    Reliability
      Offline capability
      Retry logic
      Circuit breaker
      Dead letter queue
```

---

## Implementation Checklist

### Phase 1: Setup (Week 1)

- [ ] Install Celery and Redis
- [ ] Create HRMS adapter base class
- [ ] Implement mock adapter for testing
- [ ] Set up Celery Beat scheduler

### Phase 2: Core Sync (Week 2)

- [ ] Implement employee sync task
- [ ] Implement candidate sync task
- [ ] Implement interview sync task
- [ ] Add sync status tracker

### Phase 3: Optimization (Week 3)

- [ ] Add incremental sync logic
- [ ] Implement bulk database operations
- [ ] Add Redis caching layer
- [ ] Optimize database queries

### Phase 4: Production (Week 4)

- [ ] Add error handling and retries
- [ ] Implement monitoring dashboard
- [ ] Set up alerts and notifications
- [ ] Security audit and encryption
- [ ] Load testing and performance tuning

---

## Monitoring Dashboard Preview

The admin dashboard should display:

1. **Sync Status Overview**
   - Last sync time for each entity type
   - Success/failure rates
   - Records synced in last 24 hours

2. **Active Syncs**
   - Currently running sync operations
   - Progress indicators
   - Estimated completion time

3. **Error Logs**
   - Recent failures
   - Error messages
   - Retry attempts

4. **Performance Metrics**
   - Average sync duration
   - API response times
   - Database write performance

---

_For complete implementation details, see [HR_INTEGRATION.md](./HR_INTEGRATION.md)_
