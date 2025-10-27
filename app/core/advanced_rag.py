"""
Pipeline RAG avancé avec support multi-documents et techniques d'optimisation.
"""

import os
import time
from typing import List, Dict, Any, Optional, Tuple
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.schema import Document
from sqlalchemy.orm import Session
import structlog
from app.core.database import ChatSession, Document as DBDocument, Conversation, get_db, create_tables
import uuid
from datetime import datetime

# Configuration du logger structuré
logger = structlog.get_logger(__name__)

class AdvancedRAGPipeline:
    """Pipeline RAG avancé avec support multi-documents et optimisations."""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.vector_store = None
        self.qa_chain = None
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        
        # Configuration avancée
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.max_docs_for_context = 5
        self.use_compression = True
        
        # Métriques
        self.processing_stats = {
            "documents_processed": 0,
            "total_chunks": 0,
            "last_processing_time": 0
        }
        
        # Créer les tables si nécessaire
        create_tables()
        
        logger.info("Advanced RAG Pipeline initialized", session_id=self.session_id)

    def create_or_load_session(self, session_name: str = None) -> str:
        """Crée une nouvelle session ou charge une session existante."""
        db = next(get_db())
        try:
            if session_name:
                # Vérifier si une session avec ce nom existe déjà
                existing_session = db.query(ChatSession).filter(
                    ChatSession.name == session_name,
                    ChatSession.is_active == True
                ).first()
                
                if existing_session:
                    self.session_id = existing_session.id
                    logger.info("Loaded existing session", session_id=self.session_id, name=session_name)
                    return self.session_id
            
            # Créer une nouvelle session
            session = ChatSession(
                id=self.session_id,
                name=session_name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            
            db.add(session)
            db.commit()
            
            logger.info("Created new session", session_id=self.session_id, name=session.name)
            return self.session_id
            
        finally:
            db.close()

    def process_document(self, pdf_path: str, original_filename: str) -> Dict[str, Any]:
        """
        Traite un document PDF et l'ajoute à la base de connaissances de la session.
        """
        start_time = time.time()
        
        logger.info("Starting document processing", 
                   filename=original_filename, 
                   session_id=self.session_id)
        
        try:
            # Chargement et découpage du document
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )
            split_docs = text_splitter.split_documents(documents)
            
            # Enrichir les métadonnées
            for i, doc in enumerate(split_docs):
                doc.metadata.update({
                    "session_id": self.session_id,
                    "source_file": original_filename,
                    "chunk_index": i,
                    "processing_timestamp": datetime.utcnow().isoformat()
                })
            
            # Créer ou mettre à jour le vector store
            vector_store_id = f"session_{self.session_id}"
            chroma_path = f"./chroma_db/{vector_store_id}"
            
            if os.path.exists(chroma_path):
                # Charger le vector store existant et ajouter les nouveaux documents
                self.vector_store = Chroma(
                    persist_directory=chroma_path,
                    embedding_function=self.embeddings
                )
                self.vector_store.add_documents(split_docs)
            else:
                # Créer un nouveau vector store
                self.vector_store = Chroma.from_documents(
                    documents=split_docs,
                    embedding=self.embeddings,
                    persist_directory=chroma_path
                )
            
            # Créer la chaîne RAG avec compression si activée
            if self.use_compression:
                base_retriever = self.vector_store.as_retriever(
                    search_kwargs={"k": self.max_docs_for_context * 2}
                )
                compressor = LLMChainExtractor.from_llm(self.llm)
                retriever = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=base_retriever
                )
            else:
                retriever = self.vector_store.as_retriever(
                    search_kwargs={"k": self.max_docs_for_context}
                )
            
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                verbose=True
            )
            
            processing_time = time.time() - start_time
            file_size = os.path.getsize(pdf_path)
            
            # Enregistrer en base de données
            db = next(get_db())
            try:
                doc_record = DBDocument(
                    session_id=self.session_id,
                    filename=f"{uuid.uuid4()}_{original_filename}",
                    original_name=original_filename,
                    file_size=file_size,
                    pages_count=len(documents),
                    chunks_count=len(split_docs),
                    processing_time=processing_time,
                    is_processed=True,
                    vector_store_id=vector_store_id
                )
                
                db.add(doc_record)
                
                # Mettre à jour l'activité de la session
                session = db.query(ChatSession).filter(ChatSession.id == self.session_id).first()
                if session:
                    session.last_activity = datetime.utcnow()
                
                db.commit()
                
            finally:
                db.close()
            
            # Mettre à jour les statistiques
            self.processing_stats["documents_processed"] += 1
            self.processing_stats["total_chunks"] += len(split_docs)
            self.processing_stats["last_processing_time"] = processing_time
            
            logger.info("Document processed successfully",
                       filename=original_filename,
                       chunks_count=len(split_docs),
                       processing_time=processing_time,
                       session_id=self.session_id)
            
            return {
                "success": True,
                "filename": original_filename,
                "chunks_count": len(split_docs),
                "pages_count": len(documents),
                "processing_time": processing_time,
                "vector_store_id": vector_store_id
            }
            
        except Exception as e:
            logger.error("Document processing failed", 
                        filename=original_filename, 
                        error=str(e),
                        session_id=self.session_id)
            raise

    def load_session_documents(self, session_id: str = None):
        """Charge tous les documents d'une session existante."""
        target_session = session_id or self.session_id
        
        try:
            vector_store_id = f"session_{target_session}"
            chroma_path = f"./chroma_db/{vector_store_id}"
            
            if os.path.exists(chroma_path):
                self.vector_store = Chroma(
                    persist_directory=chroma_path,
                    embedding_function=self.embeddings
                )
                
                # Recréer la chaîne RAG
                if self.use_compression:
                    base_retriever = self.vector_store.as_retriever(
                        search_kwargs={"k": self.max_docs_for_context * 2}
                    )
                    compressor = LLMChainExtractor.from_llm(self.llm)
                    retriever = ContextualCompressionRetriever(
                        base_compressor=compressor,
                        base_retriever=base_retriever
                    )
                else:
                    retriever = self.vector_store.as_retriever(
                        search_kwargs={"k": self.max_docs_for_context}
                    )
                
                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=self.llm,
                    chain_type="stuff",
                    retriever=retriever,
                    return_source_documents=True
                )
                
                logger.info("Session documents loaded", session_id=target_session)
                return True
            else:
                logger.warning("No vector store found for session", session_id=target_session)
                return False
                
        except Exception as e:
            logger.error("Failed to load session documents", 
                        session_id=target_session, 
                        error=str(e))
            return False

    def ask_question(self, question: str, save_conversation: bool = True) -> Dict[str, Any]:
        """
        Pose une question au système RAG et enregistre la conversation.
        """
        if not self.qa_chain:
            raise ValueError("No documents loaded. Please process documents first.")
        
        start_time = time.time()
        
        logger.info("Processing question", 
                   question=question[:100] + "..." if len(question) > 100 else question,
                   session_id=self.session_id)
        
        try:
            result = self.qa_chain.invoke({"query": question})
            response_time = time.time() - start_time
            
            # Calculer un score de confiance basique
            confidence_score = self._calculate_confidence_score(result)
            
            # Structurer les sources
            sources = []
            if result.get("source_documents"):
                for doc in result["source_documents"]:
                    sources.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "source_file": doc.metadata.get("source_file", "Unknown")
                    })
            
            # Sauvegarder la conversation si demandé
            if save_conversation:
                db = next(get_db())
                try:
                    conversation = Conversation(
                        session_id=self.session_id,
                        question=question,
                        answer=result["result"],
                        sources_count=len(sources),
                        response_time=response_time,
                        confidence_score=confidence_score,
                        model_used="gpt-3.5-turbo",
                        retrieval_method="similarity_with_compression" if self.use_compression else "similarity"
                    )
                    
                    db.add(conversation)
                    
                    # Mettre à jour l'activité de la session
                    session = db.query(ChatSession).filter(ChatSession.id == self.session_id).first()
                    if session:
                        session.last_activity = datetime.utcnow()
                    
                    db.commit()
                    
                finally:
                    db.close()
            
            logger.info("Question processed successfully",
                       response_time=response_time,
                       sources_count=len(sources),
                       confidence_score=confidence_score,
                       session_id=self.session_id)
            
            return {
                "answer": result["result"],
                "sources": sources,
                "response_time": response_time,
                "confidence_score": confidence_score,
                "session_id": self.session_id
            }
            
        except Exception as e:
            logger.error("Question processing failed", 
                        question=question[:100],
                        error=str(e),
                        session_id=self.session_id)
            raise

    def _calculate_confidence_score(self, result: Dict) -> float:
        """Calcule un score de confiance basique pour la réponse."""
        try:
            # Facteurs simples pour estimer la confiance
            source_count = len(result.get("source_documents", []))
            answer_length = len(result.get("result", ""))
            
            # Score basé sur la disponibilité des sources et longueur de réponse
            if source_count == 0:
                return 0.1
            elif source_count >= 3 and answer_length > 100:
                return 0.9
            elif source_count >= 2 and answer_length > 50:
                return 0.7
            else:
                return 0.5
                
        except Exception:
            return 0.5

    def get_session_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de la session courante."""
        db = next(get_db())
        try:
            session = db.query(ChatSession).filter(ChatSession.id == self.session_id).first()
            documents = db.query(DBDocument).filter(DBDocument.session_id == self.session_id).all()
            conversations = db.query(Conversation).filter(Conversation.session_id == self.session_id).all()
            
            return {
                "session_id": self.session_id,
                "session_name": session.name if session else "Unknown",
                "created_at": session.created_at.isoformat() if session else None,
                "documents_count": len(documents),
                "conversations_count": len(conversations),
                "total_chunks": sum(doc.chunks_count for doc in documents if doc.chunks_count),
                "processing_stats": self.processing_stats,
                "avg_response_time": sum(conv.response_time for conv in conversations if conv.response_time) / len(conversations) if conversations else 0
            }
            
        finally:
            db.close()
