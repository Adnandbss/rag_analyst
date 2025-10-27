# Documentation API - RAG Analyst v2.0

## Introduction

Cette API permet d'interagir avec le système RAG-Analyst pour analyser des documents PDF avec l'IA générative.

**Base URL:** `http://127.0.0.1:8000`  
**Documentation interactive:** `http://127.0.0.1:8000/docs`  
**Format:** JSON  
**Authentication:** Aucune (dev) | JWT (production)

---

## Endpoints par Catégorie

### 🔐 Sessions

#### `POST /sessions/create`
Crée une nouvelle session utilisateur.

**Request Body:**
```json
{
  "name": "Analyse Q4 2023",
  "description": "Analyse des rapports du quatrième trimestre"
}
```

**Response (200):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Analyse Q4 2023",
  "created_at": "2024-10-13T10:00:00Z",
  "last_activity": "2024-10-13T10:00:00Z",
  "documents_count": 0,
  "conversations_count": 0
}
```

#### `GET /sessions`
Liste toutes les sessions actives.

**Response (200):**
```json
[
  {
    "session_id": "...",
    "name": "...",
    "created_at": "...",
    "last_activity": "...",
    "documents_count": 2,
    "conversations_count": 15
  }
]
```

#### `GET /sessions/{session_id}/summary`
Résumé détaillé d'une session.

**Response (200):**
```json
{
  "session_id": "...",
  "session_name": "...",
  "documents_count": 2,
  "conversations_count": 15,
  "total_chunks": 250,
  "avg_response_time": 2.34,
  "processing_stats": {...}
}
```

---

### 📤 Documents

#### `POST /sessions/{session_id}/upload`
Upload et traite un document PDF.

**Form Data:**
- `file`: Fichier PDF (max 200MB)

**Response (200):**
```json
{
  "success": true,
  "filename": "rapport_annuel.pdf",
  "file_size": 2458624,
  "pages_count": 45,
  "chunks_count": 238,
  "processing_time": 15.3,
  "document_id": "doc-123"
}
```

---

### 💬 Questions & Réponses

#### `POST /ask`
Pose une question (standard ou avec agent).

**Request Body:**
```json
{
  "question": "Quel est le chiffre d'affaires ?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "enable_evaluation": false,
  "model_preference": "balanced",
  "use_agent": false
}
```

**Paramètres:**
- `question` (required): La question à poser
- `session_id` (optional): ID de session
- `enable_evaluation` (optional): Activer l'évaluation qualité
- `model_preference` (optional): "balanced", "speed", "quality", "cost"
- `use_agent` (optional): Utiliser l'agent IA avec outils

**Response (200):**
```json
{
  "answer": "Le chiffre d'affaires de l'entreprise est...",
  "sources": [
    {
      "content": "Extrait du document...",
      "metadata": {"source_file": "rapport.pdf", "page": 15}
    }
  ],
  "session_id": "...",
  "response_time": 2.34,
  "confidence_score": 0.85,
  "evaluation_result": null,
  "model_used": "gpt-3.5-turbo",
  "agent_used": false,
  "reasoning_steps": [],
  "tools_used": []
}
```

**Avec Agent Activé (`use_agent: true`):**
```json
{
  "answer": "Après avoir calculé...",
  "agent_used": true,
  "reasoning_steps": [
    {
      "tool": "calculator",
      "tool_input": "100 * 1.15",
      "observation": "Résultat : 115.0"
    }
  ],
  "tools_used": ["calculator", "document_query"]
}
```

#### `POST /ask-stream`
Pose une question avec réponse en streaming (SSE).

**Request:** Identique à `/ask`

**Response:** Server-Sent Events stream
```
data: {"type": "start", "session_id": "..."}

data: {"type": "token", "content": "Le "}

data: {"type": "token", "content": "chiffre "}

data: {"type": "sources", "sources": [...]}

data: {"type": "done", "session_id": "..."}
```

---

### 🤖 Agents

#### `GET /agents/tools`
Liste les outils disponibles pour l'agent.

**Response (200):**
```json
{
  "tools_count": 5,
  "tools": [
    {
      "name": "calculator",
      "description": "Outil de calcul mathématique..."
    },
    {
      "name": "web_search",
      "description": "Recherche web avec DuckDuckGo..."
    }
  ]
}
```

---

### 📊 Monitoring & Métriques

#### `GET /metrics`
Métriques globales du système.

**Response (200):**
```json
{
  "total_questions": 150,
  "avg_response_time": 2.45,
  "avg_confidence_score": 0.78,
  "avg_evaluation_score": 0.82,
  "error_rate": 0.02,
  "total_documents": 25,
  "total_chunks": 1250
}
```

#### `GET /metrics/prometheus`
Métriques au format Prometheus (pour scraping).

**Response (200):** Format texte Prometheus
```
# HELP rag_questions_total Nombre total de questions
# TYPE rag_questions_total counter
rag_questions_total{session_id="...",mode="rag"} 42
...
```

#### `GET /health`
Health check basique.

#### `GET /health/detailed`
Health check détaillé avec statut de chaque composant.

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-13T10:00:00Z",
  "services": {
    "database": "healthy",
    "embeddings": "healthy",
    "rate_limiter": "healthy"
  },
  "metrics": {...},
  "security": {
    "rate_limit_clients": 5,
    "active_rate_limits": 23
  }
}
```

---

### 📈 Évaluation & Tests

#### `POST /evaluation/run`
Exécute la suite de tests d'évaluation.

**Query Params:**
- `session_id` (required): Session à évaluer

**Response (200):**
```json
{
  "success": true,
  "summary": {
    "total_tests": 10,
    "passed_count": 8,
    "failed_count": 2,
    "pass_rate": 0.8,
    "average_scores": {
      "overall": 0.75,
      "relevance": 0.82
    }
  },
  "report_path": "reports/evaluation_xxx.html"
}
```

#### `GET /evaluation/results`
Résultats de la dernière évaluation.

---

### 📊 Rapports & Exports

#### `GET /reports/session/{session_id}`
Génère un rapport détaillé de session.

**Query Params:**
- `format`: "json", "html", ou "csv"

**Response (200):**
```json
{
  "session_info": {...},
  "documents_summary": {...},
  "conversations_summary": {...},
  "performance_insights": {...},
  "recommendations": [...]
}
```

#### `GET /reports/system`
Analytics système globales.

**Query Params:**
- `days` (default: 30): Période d'analyse

#### `GET /export/session/{session_id}`
Exporte les données d'une session.

**Query Params:**
- `format`: "csv" ou "json"

---

### 🔧 Configuration

#### `GET /models`
Liste des modèles disponibles.

**Response (200):**
```json
{
  "available_models": {
    "llm_models": {
      "openai": ["gpt-3.5-turbo", "gpt-4"],
      "ollama": ["mistral", "llama2"]
    },
    "embedding_models": {
      "openai": ["text-embedding-ada-002"],
      "huggingface": ["all-MiniLM-L6-v2"]
    }
  },
  "current_llm": {"provider": "openai", "model": "gpt-3.5-turbo"},
  "current_embeddings": {"provider": "openai", "model": "text-embedding-ada-002"}
}
```

---

## Codes d'Erreur

| Code | Signification | Cause Typique |
|------|---------------|---------------|
| 400 | Bad Request | Validation échouée, paramètres invalides |
| 404 | Not Found | Session ou ressource inexistante |
| 429 | Too Many Requests | Rate limit dépassé |
| 500 | Internal Server Error | Erreur serveur, check logs |
| 503 | Service Unavailable | Base de données ou OpenAI indisponible |

## Rate Limiting

- **Limite:** 100 requêtes par heure par IP
- **Header de réponse:** `X-RateLimit-Remaining`
- **Réponse 429:**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 3600
}
```

## Exemples d'Utilisation

### Python
```python
import requests

API_URL = "http://127.0.0.1:8000"

# Créer une session
session = requests.post(f"{API_URL}/sessions/create", 
    json={"name": "Test Session"}).json()

# Upload un PDF
with open("document.pdf", "rb") as f:
    response = requests.post(
        f"{API_URL}/sessions/{session['session_id']}/upload",
        files={"file": f}
    )

# Poser une question
answer = requests.post(f"{API_URL}/ask",
    json={
        "question": "Résume ce document",
        "session_id": session["session_id"]
    }).json()

print(answer["answer"])
```

### cURL
```bash
# Créer une session
curl -X POST http://127.0.0.1:8000/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"name": "Test"}'

# Poser une question
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Test?", "session_id": "..."}'
```

---

## Support & Contact

- Documentation complète : `/docs` (Swagger UI)
- Issues : GitHub Issues
- Architecture : Voir `ARCHITECTURE.md`

