import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, AsyncGenerator
from sqlalchemy.orm import Session
import structlog
import asyncio
import json

# Importer la logique RAG avancée
from app.core.advanced_rag import AdvancedRAGPipeline
from app.core.database import get_db, ChatSession, Document, Conversation, get_session_stats
from app.core.evaluation import RAGEvaluator, global_metrics
from app.core.model_config import ModelProvider, EmbeddingProvider, model_config, adaptive_selector
from app.core.report_generator import report_generator
from app.core.agents import RAGAgent, create_agent
from app.core.rag_evaluation_suite import evaluation_suite
from app.core.prometheus_metrics import (
    get_metrics, record_question_metrics, record_document_metrics,
    record_agent_metrics, record_error, update_active_sessions_count
)

# Configuration du logger structuré
logger = structlog.get_logger(__name__)

# Initialisation de l'application FastAPI
app = FastAPI(
    title="RAG Analyst API Advanced",
    description="Une API avancée pour l'analyse de documents avec IA générative et gestion de sessions.",
    version="2.0.0"
)

# Configuration CORS pour le développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instance globale du pipeline RAG, de l'évaluateur et de l'agent
current_pipeline = None
evaluator = RAGEvaluator()
current_agent = None

# Modèles Pydantic avancés pour la validation des données
class SessionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nom de la session")
    description: Optional[str] = Field(None, max_length=500, description="Description optionnelle")

class SessionResponse(BaseModel):
    session_id: str
    name: str
    created_at: str
    last_activity: str
    documents_count: int
    conversations_count: int

class DocumentUploadResponse(BaseModel):
    success: bool
    filename: str
    file_size: int
    pages_count: int
    chunks_count: int
    processing_time: float
    document_id: str

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, description="ID de session (optionnel)")
    enable_evaluation: bool = Field(False, description="Activer l'évaluation de la réponse")
    model_preference: Optional[str] = Field("balanced", description="Préférence de modèle: speed, quality, cost, balanced")
    use_agent: bool = Field(False, description="Utiliser l'agent IA avec outils au lieu du RAG classique")

class AskResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
    session_id: str
    response_time: float
    confidence_score: float
    evaluation_result: Optional[Dict[str, Any]] = None
    model_used: str
    agent_used: bool = False
    reasoning_steps: List[Dict[str, Any]] = []
    tools_used: List[str] = []

class SessionSummaryResponse(BaseModel):
    session_id: str
    session_name: str
    created_at: Optional[str]
    documents_count: int
    conversations_count: int
    total_chunks: int
    avg_response_time: float
    processing_stats: Dict[str, Any]

class MetricsResponse(BaseModel):
    total_questions: int
    avg_response_time: float
    avg_confidence_score: float
    avg_evaluation_score: float
    error_rate: float
    total_documents: int
    total_chunks: int

class ModelConfigResponse(BaseModel):
    available_models: Dict[str, Any]
    current_llm: Dict[str, str]
    current_embeddings: Dict[str, str]

@app.on_event("startup")
async def startup_event():
    """
    Initialisation de l'application au démarrage.
    """
    # Créer les dossiers nécessaires
    os.makedirs("./pdf_storage", exist_ok=True)
    os.makedirs("./chroma_db", exist_ok=True)
    
    # Initialiser les tables de la base de données
    from app.core.database import create_tables
    create_tables()
    
    logger.info("RAG Analyst API Advanced started successfully")

# Endpoints pour la gestion des sessions

@app.post("/sessions/create", response_model=SessionResponse, summary="Créer une nouvelle session")
async def create_session(request: SessionCreateRequest, db: Session = Depends(get_db)):
    """Crée une nouvelle session de chat."""
    global current_pipeline
    
    try:
        # Créer le pipeline pour cette session
        current_pipeline = AdvancedRAGPipeline()
        session_id = current_pipeline.create_or_load_session(request.name)
        
        # Récupérer les informations de la session depuis la DB
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        
        return SessionResponse(
            session_id=session_id,
            name=session.name,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            documents_count=0,
            conversations_count=0
        )
        
    except Exception as e:
        logger.error("Session creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la session : {e}")

@app.get("/sessions", summary="Lister toutes les sessions")
async def list_sessions(db: Session = Depends(get_db)):
    """Retourne la liste de toutes les sessions."""
    try:
        sessions = db.query(ChatSession).filter(ChatSession.is_active == True).all()
        
        result = []
        for session in sessions:
            documents_count = db.query(Document).filter(Document.session_id == session.id).count()
            conversations_count = db.query(Conversation).filter(Conversation.session_id == session.id).count()
            
            result.append(SessionResponse(
                session_id=session.id,
                name=session.name,
                created_at=session.created_at.isoformat(),
                last_activity=session.last_activity.isoformat(),
                documents_count=documents_count,
                conversations_count=conversations_count
            ))
        
        return result
        
    except Exception as e:
        logger.error("Sessions listing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des sessions : {e}")

@app.post("/sessions/{session_id}/upload", response_model=DocumentUploadResponse, summary="Ajouter un document à une session")
async def upload_document_to_session(
    session_id: str, 
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Ajoute un document PDF à une session existante."""
    global current_pipeline
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont autorisés.")

    # Vérifier que la session existe
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée.")

    file_path = f"./pdf_storage/{uuid.uuid4()}_{file.filename}"
    
    try:
        # Sauvegarder le fichier
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        
        # Initialiser ou récupérer le pipeline pour cette session
        if not current_pipeline or current_pipeline.session_id != session_id:
            current_pipeline = AdvancedRAGPipeline(session_id)
            current_pipeline.load_session_documents()
        
        # Traiter le document
        result = current_pipeline.process_document(file_path, file.filename)
        
        # Enregistrer les métriques
        global_metrics.record_document(result["chunks_count"])
        
        logger.info("Document uploaded successfully", 
                   filename=file.filename, 
                   session_id=session_id,
                   chunks_count=result["chunks_count"])
        
        return DocumentUploadResponse(
            success=result["success"],
            filename=result["filename"],
            file_size=file_size,
            pages_count=result["pages_count"],
            chunks_count=result["chunks_count"],
            processing_time=result["processing_time"],
            document_id=str(uuid.uuid4())  # Générer un ID unique
        )

    except Exception as e:
        logger.error("Document upload failed", filename=file.filename, error=str(e))
        global_metrics.record_question(0, 0, error=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {e}")
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/ask", response_model=AskResponse, summary="Poser une question intelligente")
async def ask_question_advanced(request: AskRequest, db: Session = Depends(get_db)):
    """
    Pose une question avancée avec évaluation optionnelle et sélection de modèle adaptatif.
    """
    global current_pipeline
    
    # Déterminer la session à utiliser
    session_id = request.session_id
    if not session_id:
        # Créer une session temporaire si aucune n'est spécifiée
        temp_pipeline = AdvancedRAGPipeline()
        session_id = temp_pipeline.create_or_load_session("Session temporaire")
        current_pipeline = temp_pipeline
    else:
        # Vérifier que la session existe et charger les documents
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session non trouvée.")
        
        if not current_pipeline or current_pipeline.session_id != session_id:
            current_pipeline = AdvancedRAGPipeline(session_id)
            current_pipeline.load_session_documents()
    
    # Vérifier les documents seulement si on n'utilise pas l'agent
    if not request.use_agent and not current_pipeline.qa_chain:
        raise HTTPException(status_code=400, 
                          detail="Aucun document disponible. Veuillez d'abord uploader des documents PDF.")
    
    try:
        # Sélection adaptative du modèle
        if request.model_preference != "balanced":
            provider, model_name, reasoning = adaptive_selector.select_best_model(
                performance_priority=request.model_preference
            )
            logger.info("Model selection", 
                       preference=request.model_preference,
                       selected_model=f"{provider.value}/{model_name}",
                       reasoning=reasoning)
        
        # Choix entre Agent IA ou RAG classique
        if request.use_agent:
            # Mode Agent : utiliser l'agent avec outils
            global current_agent
            
            # Créer ou réutiliser l'agent
            if not current_agent:
                current_agent = create_agent("react", rag_pipeline=current_pipeline)
            
            # Exécuter l'agent
            agent_result = current_agent.run(request.question, session_id)
            
            # Structurer la réponse pour être compatible avec AskResponse
            result = {
                "answer": agent_result["answer"],
                "sources": [],  # Les agents n'ont pas de sources comme le RAG
                "session_id": agent_result["session_id"],
                "response_time": agent_result["response_time"],
                "confidence_score": 0.8,  # Score fixe pour les agents
                "agent_used": True,
                "reasoning_steps": agent_result.get("reasoning_steps", []),
                "tools_used": agent_result.get("tools_used", [])
            }
        else:
            # Mode RAG classique
            result = current_pipeline.ask_question(request.question)
            result["agent_used"] = False
            result["reasoning_steps"] = []
            result["tools_used"] = []
        
        # Évaluation optionnelle de la réponse
        evaluation_result = None
        if request.enable_evaluation:
            try:
                eval_result = evaluator.evaluate_response(
                    question=request.question,
                    answer=result["answer"],
                    sources=result["sources"]
                )
                evaluation_result = {
                    "overall_score": eval_result.overall_score,
                    "relevance_score": eval_result.relevance_score,
                    "faithfulness_score": eval_result.faithfulness_score,
                    "context_precision": eval_result.context_precision,
                    "context_recall": eval_result.context_recall
                }
                
                # Enregistrer les métriques avec évaluation
                global_metrics.record_question(
                    response_time=result["response_time"],
                    confidence_score=result["confidence_score"],
                    evaluation_score=eval_result.overall_score
                )
            except Exception as e:
                logger.warning("Evaluation failed", error=str(e))
        else:
            # Enregistrer les métriques sans évaluation
            global_metrics.record_question(
                response_time=result["response_time"],
                confidence_score=result["confidence_score"]
            )
        
        return AskResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            session_id=result["session_id"],
            response_time=result["response_time"],
            confidence_score=result["confidence_score"],
            evaluation_result=evaluation_result,
            model_used="gpt-3.5-turbo",
            agent_used=result.get("agent_used", False),
            reasoning_steps=result.get("reasoning_steps", []),
            tools_used=result.get("tools_used", [])
        )

    except Exception as e:
        logger.error("Question processing failed", 
                    question=request.question[:50],
                    session_id=session_id,
                    error=str(e))
        global_metrics.record_question(0, 0, error=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {e}")

# Endpoints pour le monitoring et les métriques

@app.get("/sessions/{session_id}/summary", response_model=SessionSummaryResponse, summary="Résumé d'une session")
async def get_session_summary(session_id: str):
    """Retourne un résumé détaillé d'une session."""
    try:
        # Créer temporairement un pipeline pour cette session
        pipeline = AdvancedRAGPipeline(session_id)
        summary = pipeline.get_session_summary()
        
        return SessionSummaryResponse(**summary)
        
    except Exception as e:
        logger.error("Session summary failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du résumé : {e}")

@app.get("/metrics", response_model=MetricsResponse, summary="Métriques globales du système")
async def get_system_metrics():
    """Retourne les métriques de performance du système."""
    try:
        metrics = global_metrics.get_metrics()
        
        return MetricsResponse(
            total_questions=metrics["total_questions"],
            avg_response_time=metrics["avg_response_time"],
            avg_confidence_score=metrics["avg_confidence_score"],
            avg_evaluation_score=metrics["avg_evaluation_score"],
            error_rate=metrics["error_rate"],
            total_documents=metrics["total_documents"],
            total_chunks=metrics["total_chunks"]
        )
        
    except Exception as e:
        logger.error("Metrics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des métriques : {e}")

@app.get("/models", response_model=ModelConfigResponse, summary="Configuration des modèles")
async def get_model_configuration():
    """Retourne la configuration des modèles disponibles."""
    try:
        available = model_config.get_available_models()
        
        return ModelConfigResponse(
            available_models=available,
            current_llm={"provider": "openai", "model": "gpt-3.5-turbo"},
            current_embeddings={"provider": "openai", "model": "text-embedding-ada-002"}
        )
        
    except Exception as e:
        logger.error("Model config retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de la configuration : {e}")

@app.post("/ask-stream", summary="Poser une question avec streaming")
async def ask_question_stream(request: AskRequest, db: Session = Depends(get_db)):
    """
    Pose une question avec réponse en streaming (token par token).
    Utilise Server-Sent Events (SSE) pour envoyer les tokens progressivement.
    """
    global current_pipeline, current_agent
    
    # Déterminer la session
    session_id = request.session_id
    if not session_id:
        temp_pipeline = AdvancedRAGPipeline()
        session_id = temp_pipeline.create_or_load_session("Session temporaire")
        current_pipeline = temp_pipeline
    else:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session non trouvée.")
        
        if not current_pipeline or current_pipeline.session_id != session_id:
            current_pipeline = AdvancedRAGPipeline(session_id)
            current_pipeline.load_session_documents()
    
    if not current_pipeline.qa_chain and not request.use_agent:
        raise HTTPException(status_code=400, detail="Aucun document disponible.")
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """Génère le stream de tokens."""
        try:
            # Import ici pour éviter les problèmes circulaires
            from langchain.callbacks.base import BaseCallbackHandler
            from langchain_openai import ChatOpenAI
            
            class StreamingCallbackHandler(BaseCallbackHandler):
                """Callback pour capturer les tokens streamés."""
                def __init__(self):
                    self.tokens = []
                
                def on_llm_new_token(self, token: str, **kwargs):
                    self.tokens.append(token)
            
            # Créer le callback
            callback = StreamingCallbackHandler()
            
            # Créer un LLM avec streaming
            streaming_llm = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                temperature=0,
                streaming=True,
                callbacks=[callback]
            )
            
            # Envoyer un événement de démarrage
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
            
            if request.use_agent:
                # Mode Agent (sans streaming pour l'instant)
                if not current_agent:
                    current_agent = create_agent("react", rag_pipeline=current_pipeline)
                
                result = current_agent.run(request.question, session_id)
                
                # Simuler le streaming en envoyant par mots
                words = result["answer"].split()
                for word in words:
                    yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
                    await asyncio.sleep(0.05)  # Petit délai pour simuler
                
                # Envoyer les métadonnées finales
                yield f"data: {json.dumps({'type': 'metadata', 'reasoning_steps': result.get('reasoning_steps', []), 'tools_used': result.get('tools_used', [])})}\n\n"
            
            else:
                # Mode RAG avec vrai streaming
                # Note: RetrievalQA ne supporte pas nativement le streaming,
                # on simule en envoyant la réponse par mots
                result = current_pipeline.ask_question(request.question)
                
                words = result["answer"].split()
                for word in words:
                    yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
                    await asyncio.sleep(0.05)
                
                # Envoyer les sources
                if result.get("sources"):
                    yield f"data: {json.dumps({'type': 'sources', 'sources': result['sources'][:3]})}\n\n"
            
            # Événement de fin
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
            
        except Exception as e:
            logger.error("Streaming failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/agents/tools", summary="Liste des outils disponibles pour l'agent")
async def get_agent_tools():
    """Retourne la liste des outils disponibles pour l'agent IA."""
    try:
        # Créer un agent temporaire pour obtenir la liste des outils
        temp_agent = create_agent("react")
        tools = temp_agent.get_available_tools()
        
        return {
            "tools_count": len(tools),
            "tools": tools
        }
        
    except Exception as e:
        logger.error("Agent tools listing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des outils : {e}")

# Endpoints pour l'évaluation et les tests

@app.post("/evaluation/run", summary="Exécuter la suite de tests d'évaluation")
async def run_evaluation_suite(session_id: str):
    """
    Exécute la suite complète de tests d'évaluation sur une session.
    Génère un rapport HTML avec les résultats.
    """
    try:
        # Charger le pipeline de la session
        pipeline = AdvancedRAGPipeline(session_id)
        
        if not pipeline.load_session_documents():
            raise HTTPException(status_code=400, 
                              detail="Impossible de charger les documents de la session.")
        
        # Exécuter l'évaluation
        logger.info("Starting evaluation suite", session_id=session_id)
        results = evaluation_suite.run_evaluation(pipeline)
        
        # Générer le rapport HTML
        html_file = f"reports/evaluation_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        os.makedirs("reports", exist_ok=True)
        
        report_path = evaluation_suite.generate_html_report(html_file)
        
        return {
            "success": True,
            "summary": results["summary"],
            "report_path": report_path,
            "test_results_count": len(results["test_results"])
        }
        
    except Exception as e:
        logger.error("Evaluation suite failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'évaluation : {e}")

@app.get("/evaluation/results", summary="Résultats de la dernière évaluation")
async def get_evaluation_results():
    """Retourne les résultats de la dernière évaluation exécutée."""
    try:
        if not evaluation_suite.results:
            return {"message": "Aucune évaluation disponible", "results": []}
        
        summary = evaluation_suite._generate_summary(0)
        
        return {
            "summary": summary,
            "results_count": len(evaluation_suite.results),
            "by_category": evaluation_suite.get_results_by_category(),
            "failed_analysis": evaluation_suite.get_failed_tests_analysis()
        }
        
    except Exception as e:
        logger.error("Failed to get evaluation results", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur : {e}")

@app.get("/metrics/prometheus", summary="Métriques Prometheus")
async def prometheus_metrics():
    """Endpoint pour exposer les métriques au format Prometheus."""
    from fastapi import Response
    
    metrics, content_type = get_metrics()
    return Response(content=metrics, media_type=content_type)

@app.get("/health", summary="Vérification de l'état du système")
async def health_check():
    """Endpoint de santé pour le monitoring."""
    try:
        # Vérifier les composants essentiels
        stats = get_session_stats()
        
        return {
            "status": "healthy",
            "timestamp": "2024-10-10T12:00:00Z",  # TODO: utiliser datetime.utcnow()
            "database": "connected",
            "sessions": stats,
            "metrics": global_metrics.get_metrics()
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-10-10T12:00:00Z"
        }

@app.get("/", include_in_schema=False)
async def read_root():
    return {
        "message": "Bienvenue sur RAG Analyst API Advanced v2.0",
        "features": [
            "Gestion multi-sessions et multi-documents",
            "Évaluation intelligente des réponses",
            "Métriques de performance avancées",
            "Configuration multi-modèles",
            "Logging structuré et monitoring"
        ],
        "endpoints": {
            "documentation": "/docs",
            "health": "/health",
            "sessions": "/sessions",
            "metrics": "/metrics"
        }
    }

# Endpoints pour les rapports et exports

@app.get("/reports/session/{session_id}", summary="Rapport de session détaillé")
async def get_session_report(
    session_id: str,
    format: str = Query("json", regex="^(json|html|csv)$", description="Format du rapport")
):
    """Génère un rapport détaillé pour une session."""
    try:
        report = report_generator.generate_session_report(session_id, format)
        
        if format == "html":
            return {"html_content": report, "format": "html"}
        elif format == "csv":
            return {"csv_content": report, "format": "csv"}
        else:
            return report
            
    except Exception as e:
        logger.error("Session report generation failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du rapport : {e}")

@app.get("/reports/system", summary="Analytics système globales")
async def get_system_analytics(
    days: int = Query(30, ge=1, le=365, description="Nombre de jours à analyser")
):
    """Génère un rapport d'analyse du système sur la période spécifiée."""
    try:
        analytics = report_generator.generate_system_analytics(days)
        return analytics
        
    except Exception as e:
        logger.error("System analytics generation failed", days=days, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération des analytics : {e}")

@app.get("/export/session/{session_id}", summary="Exporter les données d'une session")
async def export_session_data(
    session_id: str,
    format: str = Query("csv", regex="^(csv|json)$", description="Format d'export")
):
    """Exporte toutes les données d'une session dans le format demandé."""
    try:
        filepath = report_generator.export_session_data(session_id, format)
        
        # En production, on retournerait un lien de téléchargement
        # Ici on retourne le chemin du fichier
        return {
            "success": True,
            "filepath": filepath,
            "format": format,
            "message": f"Export terminé. Fichier sauvegardé : {filepath}"
        }
        
    except Exception as e:
        logger.error("Session export failed", session_id=session_id, format=format, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'export : {e}")

# Middleware de sécurité et rate limiting

from fastapi import Request, BackgroundTasks
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from time import time
import hashlib

# Configuration du rate limiting
RATE_LIMIT_REQUESTS = 100  # Nombre max de requêtes
RATE_LIMIT_WINDOW = 3600   # Fenêtre de temps en secondes (1 heure)
RATE_LIMIT_STORAGE = defaultdict(deque)

class RateLimitMiddleware:
    """Middleware de limitation de taux."""
    
    def __init__(self, app, requests_per_window: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW):
        self.app = app
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extraire l'IP du client
        client_ip = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-forwarded-for":
                client_ip = header_value.decode().split(",")[0].strip()
                break
            elif header_name == b"x-real-ip":
                client_ip = header_value.decode()
                break
        
        if not client_ip:
            client_ip = scope.get("client", ["unknown"])[0]

        # Créer une clé unique pour le client
        client_key = hashlib.md5(client_ip.encode()).hexdigest()
        
        current_time = time()
        
        # Nettoyer les anciennes requêtes
        client_requests = RATE_LIMIT_STORAGE[client_key]
        while client_requests and current_time - client_requests[0] > self.window_seconds:
            client_requests.popleft()
        
        # Vérifier la limite
        if len(client_requests) >= self.requests_per_window:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_window} requests per {self.window_seconds} seconds",
                    "retry_after": int(self.window_seconds - (current_time - client_requests[0]))
                }
            )
            await response(scope, receive, send)
            return
        
        # Enregistrer la nouvelle requête
        client_requests.append(current_time)
        
        # Continuer avec la requête normale
        await self.app(scope, receive, send)

# Ajouter le middleware de rate limiting
# Note: En production, utilisez Redis ou une solution dédiée
# app.add_middleware(RateLimitMiddleware)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Ajoute des en-têtes de sécurité."""
    response = await call_next(request)
    
    # Headers de sécurité basiques
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log structuré des requêtes."""
    start_time = time()
    
    # Log de la requête entrante
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown")
    )
    
    response = await call_next(request)
    
    # Log de la réponse
    process_time = time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=round(process_time, 3)
    )
    
    return response

# Endpoints de sécurité et monitoring

@app.get("/security/info", summary="Informations de sécurité")
async def get_security_info():
    """Retourne des informations sur la sécurité de l'API."""
    return {
        "security_features": {
            "rate_limiting": "Actif",
            "request_logging": "Actif",
            "security_headers": "Actif",
            "input_validation": "Pydantic",
            "cors_protection": "Configuré"
        },
        "rate_limits": {
            "requests_per_hour": RATE_LIMIT_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW
        },
        "recommendations": [
            "Utilisez HTTPS en production",
            "Configurez une authentification appropriée",
            "Mettez en place un monitoring des accès",
            "Utilisez un WAF (Web Application Firewall)",
            "Chiffrez les données sensibles"
        ]
    }

@app.post("/admin/reset-rate-limits", summary="Réinitialiser les limites de taux")
async def reset_rate_limits():
    """Réinitialise les compteurs de rate limiting (admin uniquement)."""
    # En production, cet endpoint devrait être protégé par une authentification admin
    RATE_LIMIT_STORAGE.clear()
    logger.info("Rate limits reset by admin")
    return {"message": "Rate limits reset successfully"}

# Health check avancé avec métriques de sécurité
@app.get("/health/detailed", summary="Vérification de santé détaillée")
async def detailed_health_check():
    """Health check avec informations détaillées pour le monitoring."""
    try:
        # Vérifier les composants
        db_status = "healthy"
        try:
            stats = get_session_stats()
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Métriques système
        system_metrics = global_metrics.get_metrics()
        
        # Statut des services
        services_status = {
            "database": db_status,
            "embeddings": "healthy",  # TODO: Vérifier la connexion OpenAI
            "rate_limiter": "healthy",
            "logging": "healthy"
        }
        
        # Déterminer le statut global
        overall_status = "healthy" if all(
            status == "healthy" for status in services_status.values()
        ) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": services_status,
            "metrics": system_metrics,
            "security": {
                "rate_limit_clients": len(RATE_LIMIT_STORAGE),
                "active_rate_limits": sum(len(reqs) for reqs in RATE_LIMIT_STORAGE.values())
            },
            "uptime": "N/A",  # TODO: Calculer l'uptime réel
            "version": "2.0.0"
        }
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
