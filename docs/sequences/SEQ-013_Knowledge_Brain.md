# SEQ-013: Knowledge Brain Query & Storage

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Any Agent
    participant Brain as AgentBrain
    participant Mem as In-Memory Cache
    participant KB as knowledge_entries (DB)
    participant KG as KnowledgeGraph
    participant PM as ProjectMemoryService

    rect rgb(240, 248, 255)
        Note over Agent,Brain: STORE Operation
        Agent->>Brain: store_knowledge(agent_id, entry_type, tender_id, data, summary, tags)
        Brain->>Mem: cache.set(key, entry)
        Brain->>KB: INSERT INTO knowledge_entries (entry_type, tender_id, agent_id, data, summary, tags, source, created_at)
        Brain-->>Agent: { stored: true, entry_id }
    end

    rect rgb(240, 255, 240)
        Note over Agent,Brain: QUERY Operation (by type + tender_id)
        Agent->>Brain: query_brain(entry_type, tender_id)
        Brain->>Mem: cache.get(key)
        alt Cache HIT
            Mem-->>Brain: cached entry
        else Cache MISS
            Brain->>KB: SELECT * FROM knowledge_entries WHERE entry_type=$1 AND tender_id=$2
            KB-->>Brain: entry row
            Brain->>Mem: cache.set(key, entry)
        end
        Brain-->>Agent: knowledge_entry
    end

    rect rgb(255, 248, 240)
        Note over Agent,Brain: SEARCH Operation (text search)
        Agent->>Brain: search_knowledge(query, filters)
        Brain->>KB: SELECT * FROM knowledge_entries WHERE ts_vector @@ plainto_tsquery($1) LIMIT 20
        KB-->>Brain: matching entries
        Brain-->>Agent: knowledge_entry[]
    end

    rect rgb(248, 240, 255)
        Note over Agent,KG: GRAPH TRAVERSAL
        Agent->>Brain: traverse_knowledge(tender_id, depth=2)
        Brain->>KG: get_neighbors(tender_id, depth)
        KG->>KB: SELECT * FROM knowledge_graph_nodes WHERE entity_id=$1
        KG->>KB: SELECT * FROM knowledge_graph_edges WHERE source=$1 OR target=$1
        KB-->>KG: nodes + edges
        KG-->>Brain: graph subgraph
        Brain-->>Agent: { nodes: [...], edges: [...] }
    end

    rect rgb(255, 240, 240)
        Note over Agent,PM: HYBRID SEARCH (lexical + vector)
        Agent->>PM: hybrid_search(query, limit)
        PM->>KB: Lexical: ts_vector @@ plainto_tsquery
        PM->>KB: Vector: embedding <=> query_embedding (cosine)
        PM->>PM: RRF fusion (Reciprocal Rank Fusion)
        PM-->>Agent: ranked results[]
    end

    rect rgb(240, 255, 248)
        Note over Agent,Brain: SYNC Operation (startup)
        Note over Brain: On app startup
        Brain->>KB: SELECT * FROM knowledge_entries ORDER BY created_at DESC LIMIT 10000
        KB-->>Brain: all entries
        Brain->>Mem: bulk cache warm
        Brain-->>Brain: cache ready
    end
```

## Knowledge Entry Types

| entry_type | Content | Stored By |
|------------|---------|-----------|
| `tender_document` | Full acquisition metadata | agent-002 |
| `boq_text` | Extracted BOQ text (50K chars) | agent-002 |
| `tds_text` | Extracted TDS text (50K chars) | agent-002 |
| `pipeline_result` | Pipeline completion summary | agent-027 |
| `bid_decision` | Bid/No-Bid rationale | agent-039 |
| `rate_analysis` | Item cost breakdowns | agent-011 |
| `competitor_profile` | Competitor intelligence | agent-013 |

## Cache Strategy

| Operation | Cache | TTL | Invalidation |
|-----------|-------|-----|-------------|
| Store | Write-through | Permanent | On store |
| Query by type+tender | Read-through | 5min | On store (same key) |
| Search | No cache | — | — |
| Graph | No cache | — | — |
| Sync | Bulk warm | Permanent | On startup |
