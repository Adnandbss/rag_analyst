"""
Gestion de la base de données pour les sessions et métadonnées des documents.
"""

from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import os

# Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rag_sessions.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatSession(Base):
    """Modèle pour une session de chat utilisateur."""
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relations
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")

class Document(Base):
    """Modèle pour un document traité."""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    pages_count = Column(Integer)
    chunks_count = Column(Integer)
    processing_time = Column(Float)  # en secondes
    upload_time = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)
    vector_store_id = Column(String)  # ID dans ChromaDB
    
    # Relations
    session = relationship("ChatSession", back_populates="documents")
    
class Conversation(Base):
    """Modèle pour stocker l'historique des conversations."""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources_count = Column(Integer, default=0)
    response_time = Column(Float)  # en secondes
    confidence_score = Column(Float)  # score de confiance de la réponse
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Métadonnées pour l'évaluation
    tokens_used = Column(Integer)
    model_used = Column(String)
    retrieval_method = Column(String, default="similarity")
    
    # Relations
    session = relationship("ChatSession", back_populates="conversations")

class EvaluationMetric(Base):
    """Modèle pour stocker les métriques d'évaluation des réponses."""
    __tablename__ = "evaluation_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    
    # Métriques RAG
    relevance_score = Column(Float)  # Pertinence de la réponse
    faithfulness_score = Column(Float)  # Fidélité aux sources
    context_precision = Column(Float)  # Précision du contexte récupéré
    context_recall = Column(Float)  # Rappel du contexte
    
    # Métriques NLP classiques
    rouge_1 = Column(Float)
    rouge_2 = Column(Float)
    rouge_l = Column(Float)
    
    evaluation_time = Column(DateTime, default=datetime.utcnow)

def get_db():
    """Générateur de session de base de données."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Crée toutes les tables de la base de données."""
    Base.metadata.create_all(bind=engine)

def get_session_stats():
    """Retourne des statistiques globales sur les sessions."""
    db = SessionLocal()
    try:
        total_sessions = db.query(ChatSession).count()
        total_documents = db.query(Document).count()
        total_conversations = db.query(Conversation).count()
        active_sessions = db.query(ChatSession).filter(ChatSession.is_active == True).count()
        
        return {
            "total_sessions": total_sessions,
            "total_documents": total_documents,
            "total_conversations": total_conversations,
            "active_sessions": active_sessions
        }
    finally:
        db.close()
