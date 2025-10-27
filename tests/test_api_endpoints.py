"""
Tests pour les endpoints de l'API avancée.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import tempfile
import os
from app.main import app
from app.core.database import Base, engine

# Client de test FastAPI
client = TestClient(app)

class TestBasicEndpoints:
    """Tests pour les endpoints de base."""
    
    def test_root_endpoint(self):
        """Test de l'endpoint racine."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "features" in data
        assert "endpoints" in data
        assert "Advanced v2.0" in data["message"]

    def test_health_endpoint(self):
        """Test de l'endpoint de santé."""
        with patch('app.main.get_session_stats') as mock_stats:
            mock_stats.return_value = {
                "total_sessions": 0,
                "total_documents": 0,
                "total_conversations": 0,
                "active_sessions": 0
            }
            
            response = client.get("/health")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert "database" in data
            assert "sessions" in data
            assert "metrics" in data

    def test_metrics_endpoint(self):
        """Test de l'endpoint des métriques."""
        response = client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        expected_fields = [
            "total_questions", "avg_response_time", "avg_confidence_score",
            "avg_evaluation_score", "error_rate", "total_documents", "total_chunks"
        ]
        
        for field in expected_fields:
            assert field in data
            assert isinstance(data[field], (int, float))

    def test_models_endpoint(self):
        """Test de l'endpoint de configuration des modèles."""
        response = client.get("/models")
        assert response.status_code == 200
        
        data = response.json()
        assert "available_models" in data
        assert "current_llm" in data
        assert "current_embeddings" in data
        
        # Vérifier la structure des modèles disponibles
        available = data["available_models"]
        assert "llm_models" in available
        assert "embedding_models" in available

class TestSessionManagement:
    """Tests pour la gestion des sessions."""
    
    def setup_method(self):
        """Configuration avant chaque test."""
        # Créer les tables pour les tests
        Base.metadata.create_all(bind=engine)
    
    def test_create_session(self):
        """Test de création d'une session."""
        session_data = {
            "name": "Test Session",
            "description": "Session de test"
        }
        
        with patch('app.main.AdvancedRAGPipeline') as mock_pipeline:
            # Mock du pipeline
            mock_instance = Mock()
            mock_instance.create_or_load_session.return_value = "test-session-id"
            mock_pipeline.return_value = mock_instance
            
            # Mock de la base de données
            with patch('app.main.get_db') as mock_db:
                mock_session = Mock()
                mock_session.id = "test-session-id"
                mock_session.name = "Test Session"
                mock_session.created_at.isoformat.return_value = "2024-01-01T00:00:00"
                mock_session.last_activity.isoformat.return_value = "2024-01-01T00:00:00"
                
                mock_db_instance = Mock()
                mock_db_instance.query().filter().first.return_value = mock_session
                mock_db.return_value.__enter__.return_value = mock_db_instance
                
                response = client.post("/sessions/create", json=session_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] == "test-session-id"
                assert data["name"] == "Test Session"
                assert data["documents_count"] == 0
                assert data["conversations_count"] == 0

    def test_create_session_invalid_data(self):
        """Test de création de session avec des données invalides."""
        # Nom trop court
        response = client.post("/sessions/create", json={"name": ""})
        assert response.status_code == 422
        
        # Nom trop long
        long_name = "x" * 101  # Dépasse la limite de 100 caractères
        response = client.post("/sessions/create", json={"name": long_name})
        assert response.status_code == 422

    def test_list_sessions(self):
        """Test de listage des sessions."""
        with patch('app.main.get_db') as mock_db:
            # Mock des sessions
            mock_session1 = Mock()
            mock_session1.id = "session-1"
            mock_session1.name = "Session 1"
            mock_session1.created_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_session1.last_activity.isoformat.return_value = "2024-01-01T00:00:00"
            
            mock_session2 = Mock()
            mock_session2.id = "session-2"
            mock_session2.name = "Session 2"
            mock_session2.created_at.isoformat.return_value = "2024-01-01T01:00:00"
            mock_session2.last_activity.isoformat.return_value = "2024-01-01T01:00:00"
            
            mock_db_instance = Mock()
            mock_db_instance.query().filter().all.return_value = [mock_session1, mock_session2]
            mock_db_instance.query().filter().count.return_value = 0  # Pas de documents/conversations
            mock_db.return_value.__enter__.return_value = mock_db_instance
            
            response = client.get("/sessions")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["session_id"] == "session-1"
            assert data[1]["session_id"] == "session-2"

class TestDocumentUpload:
    """Tests pour l'upload de documents."""
    
    def test_upload_document_invalid_file_type(self):
        """Test d'upload avec un type de fichier invalide."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"Test content")
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as test_file:
                response = client.post(
                    "/sessions/test-session/upload",
                    files={"file": ("test.txt", test_file, "text/plain")}
                )
            
            assert response.status_code == 400
            assert "PDF" in response.json()["detail"]
            
        finally:
            os.unlink(temp_path)

    def test_upload_document_session_not_found(self):
        """Test d'upload sur une session inexistante."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b"Fake PDF content")
            temp_path = f.name
        
        try:
            with patch('app.main.get_db') as mock_db:
                mock_db_instance = Mock()
                mock_db_instance.query().filter().first.return_value = None
                mock_db.return_value.__enter__.return_value = mock_db_instance
                
                with open(temp_path, 'rb') as test_file:
                    response = client.post(
                        "/sessions/nonexistent-session/upload",
                        files={"file": ("test.pdf", test_file, "application/pdf")}
                    )
                
                assert response.status_code == 404
                assert "Session non trouvée" in response.json()["detail"]
                
        finally:
            os.unlink(temp_path)

class TestQuestionAnswering:
    """Tests pour les questions-réponses."""
    
    def test_ask_question_no_session(self):
        """Test de question sans session spécifiée."""
        question_data = {
            "question": "Quelle est la couleur du ciel?"
        }
        
        with patch('app.main.AdvancedRAGPipeline') as mock_pipeline:
            mock_instance = Mock()
            mock_instance.create_or_load_session.return_value = "temp-session"
            mock_instance.qa_chain = Mock()  # Pipeline initialisé
            mock_instance.ask_question.return_value = {
                "answer": "Le ciel est bleu",
                "sources": [],
                "session_id": "temp-session",
                "response_time": 1.0,
                "confidence_score": 0.8
            }
            mock_pipeline.return_value = mock_instance
            
            response = client.post("/ask", json=question_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "Le ciel est bleu"
            assert data["session_id"] == "temp-session"
            assert data["response_time"] == 1.0
            assert data["confidence_score"] == 0.8

    def test_ask_question_with_evaluation(self):
        """Test de question avec évaluation activée."""
        question_data = {
            "question": "Quelle est la couleur du ciel?",
            "enable_evaluation": True
        }
        
        with patch('app.main.AdvancedRAGPipeline') as mock_pipeline, \
             patch('app.main.evaluator') as mock_evaluator:
            
            # Mock du pipeline
            mock_instance = Mock()
            mock_instance.create_or_load_session.return_value = "temp-session"
            mock_instance.qa_chain = Mock()
            mock_instance.ask_question.return_value = {
                "answer": "Le ciel est bleu",
                "sources": [],
                "session_id": "temp-session",
                "response_time": 1.0,
                "confidence_score": 0.8
            }
            mock_pipeline.return_value = mock_instance
            
            # Mock de l'évaluateur
            mock_eval_result = Mock()
            mock_eval_result.overall_score = 0.9
            mock_eval_result.relevance_score = 0.85
            mock_eval_result.faithfulness_score = 0.95
            mock_eval_result.context_precision = 0.8
            mock_eval_result.context_recall = 0.7
            mock_evaluator.evaluate_response.return_value = mock_eval_result
            
            response = client.post("/ask", json=question_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "evaluation_result" in data
            assert data["evaluation_result"]["overall_score"] == 0.9
            assert data["evaluation_result"]["relevance_score"] == 0.85

    def test_ask_question_invalid_data(self):
        """Test de question avec des données invalides."""
        # Question vide
        response = client.post("/ask", json={"question": ""})
        assert response.status_code == 422
        
        # Question trop longue
        long_question = "x" * 1001
        response = client.post("/ask", json={"question": long_question})
        assert response.status_code == 422
        
        # Pas de question
        response = client.post("/ask", json={})
        assert response.status_code == 422

    def test_ask_question_no_documents(self):
        """Test de question sans documents chargés."""
        question_data = {
            "question": "Quelle est la couleur du ciel?"
        }
        
        with patch('app.main.AdvancedRAGPipeline') as mock_pipeline:
            mock_instance = Mock()
            mock_instance.create_or_load_session.return_value = "temp-session"
            mock_instance.qa_chain = None  # Pas de documents chargés
            mock_pipeline.return_value = mock_instance
            
            response = client.post("/ask", json=question_data)
            
            assert response.status_code == 400
            assert "Aucun document disponible" in response.json()["detail"]

class TestSessionSummary:
    """Tests pour les résumés de session."""
    
    def test_get_session_summary(self):
        """Test de récupération du résumé d'une session."""
        with patch('app.main.AdvancedRAGPipeline') as mock_pipeline:
            mock_instance = Mock()
            mock_instance.get_session_summary.return_value = {
                "session_id": "test-session",
                "session_name": "Test Session",
                "created_at": "2024-01-01T00:00:00",
                "documents_count": 2,
                "conversations_count": 5,
                "total_chunks": 100,
                "processing_stats": {"documents_processed": 2},
                "avg_response_time": 1.5
            }
            mock_pipeline.return_value = mock_instance
            
            response = client.get("/sessions/test-session/summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session"
            assert data["documents_count"] == 2
            assert data["conversations_count"] == 5
            assert data["avg_response_time"] == 1.5

class TestErrorHandling:
    """Tests pour la gestion d'erreurs."""
    
    def test_session_creation_error(self):
        """Test de gestion d'erreur lors de la création de session."""
        session_data = {"name": "Test Session"}
        
        with patch('app.main.AdvancedRAGPipeline') as mock_pipeline:
            mock_pipeline.side_effect = Exception("Database error")
            
            response = client.post("/sessions/create", json=session_data)
            
            assert response.status_code == 500
            assert "Erreur lors de la création de la session" in response.json()["detail"]

    def test_question_processing_error(self):
        """Test de gestion d'erreur lors du traitement de question."""
        question_data = {"question": "Test question"}
        
        with patch('app.main.AdvancedRAGPipeline') as mock_pipeline:
            mock_instance = Mock()
            mock_instance.create_or_load_session.return_value = "temp-session"
            mock_instance.qa_chain = Mock()
            mock_instance.ask_question.side_effect = Exception("Processing error")
            mock_pipeline.return_value = mock_instance
            
            response = client.post("/ask", json=question_data)
            
            assert response.status_code == 500
            assert "Erreur lors du traitement" in response.json()["detail"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
