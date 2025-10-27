"""
Collecteur de métriques Prometheus pour monitoring avancé.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
import structlog
import time

logger = structlog.get_logger(__name__)

# Créer un registry personnalisé
registry = CollectorRegistry()

# Métriques pour les requêtes API
api_requests_total = Counter(
    'rag_api_requests_total',
    'Nombre total de requêtes API',
    ['endpoint', 'method', 'status_code'],
    registry=registry
)

api_request_duration = Histogram(
    'rag_api_request_duration_seconds',
    'Durée des requêtes API en secondes',
    ['endpoint', 'method'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=registry
)

# Métriques pour le système RAG
rag_questions_total = Counter(
    'rag_questions_total',
    'Nombre total de questions posées',
    ['session_id', 'mode'],  # mode: rag ou agent
    registry=registry
)

rag_response_duration = Histogram(
    'rag_response_duration_seconds',
    'Durée de génération des réponses',
    ['mode'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0),
    registry=registry
)

rag_confidence_score = Histogram(
    'rag_confidence_score',
    'Scores de confiance des réponses',
    buckets=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    registry=registry
)

rag_evaluation_score = Histogram(
    'rag_evaluation_score',
    'Scores d\'évaluation des réponses',
    buckets=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    registry=registry
)

# Métriques pour les documents
documents_processed_total = Counter(
    'rag_documents_processed_total',
    'Nombre total de documents traités',
    ['session_id'],
    registry=registry
)

document_processing_duration = Histogram(
    'rag_document_processing_duration_seconds',
    'Durée de traitement des documents',
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
    registry=registry
)

document_chunks_total = Counter(
    'rag_document_chunks_total',
    'Nombre total de chunks créés',
    ['session_id'],
    registry=registry
)

# Métriques pour les sessions
active_sessions = Gauge(
    'rag_active_sessions',
    'Nombre de sessions actives',
    registry=registry
)

# Métriques pour les agents IA
agent_tool_usage = Counter(
    'rag_agent_tool_usage_total',
    'Nombre d\'utilisations des outils par l\'agent',
    ['tool_name'],
    registry=registry
)

agent_execution_duration = Histogram(
    'rag_agent_execution_duration_seconds',
    'Durée d\'exécution des agents',
    buckets=(1.0, 5.0, 10.0, 20.0, 30.0, 60.0),
    registry=registry
)

# Métriques d'erreurs
errors_total = Counter(
    'rag_errors_total',
    'Nombre total d\'erreurs',
    ['error_type', 'component'],
    registry=registry
)

# Information sur le système
system_info = Info(
    'rag_system',
    'Informations sur le système RAG',
    registry=registry
)

# Initialiser les informations système
system_info.info({
    'version': '2.0.0',
    'python_version': '3.11',
    'framework': 'LangChain + FastAPI'
})

class MetricsMiddleware:
    """Middleware pour collecter automatiquement les métriques."""
    
    def __init__(self):
        self.in_progress = Gauge(
            'rag_requests_in_progress',
            'Nombre de requêtes en cours',
            registry=registry
        )

    async def __call__(self, request, call_next):
        """Traite la requête et collecte les métriques."""
        # Incrémenter le compteur de requêtes en cours
        self.in_progress.inc()
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Enregistrer la durée
            duration = time.time() - start_time
            api_request_duration.labels(
                endpoint=request.url.path,
                method=request.method
            ).observe(duration)
            
            # Enregistrer le compteur
            api_requests_total.labels(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code
            ).inc()
            
            return response
            
        except Exception as e:
            # Enregistrer l'erreur
            errors_total.labels(
                error_type=type(e).__name__,
                component='api'
            ).inc()
            raise
            
        finally:
            # Décrémenter le compteur de requêtes en cours
            self.in_progress.dec()

def record_question_metrics(mode: str, duration: float, confidence: float, 
                            session_id: str = "default", evaluation_score: float = None):
    """Enregistre les métriques d'une question."""
    rag_questions_total.labels(session_id=session_id, mode=mode).inc()
    rag_response_duration.labels(mode=mode).observe(duration)
    rag_confidence_score.observe(confidence)
    
    if evaluation_score is not None:
        rag_evaluation_score.observe(evaluation_score)

def record_document_metrics(session_id: str, processing_duration: float, chunks_count: int):
    """Enregistre les métriques de traitement de document."""
    documents_processed_total.labels(session_id=session_id).inc()
    document_processing_duration.observe(processing_duration)
    document_chunks_total.labels(session_id=session_id).inc(chunks_count)

def record_agent_metrics(tool_name: str, duration: float):
    """Enregistre les métriques d'utilisation des outils de l'agent."""
    agent_tool_usage.labels(tool_name=tool_name).inc()
    agent_execution_duration.observe(duration)

def record_error(error_type: str, component: str):
    """Enregistre une erreur."""
    errors_total.labels(error_type=error_type, component=component).inc()

def update_active_sessions_count(count: int):
    """Met à jour le nombre de sessions actives."""
    active_sessions.set(count)

def get_metrics():
    """Retourne les métriques au format Prometheus."""
    return generate_latest(registry), CONTENT_TYPE_LATEST

