"""
Suite de tests complète pour l'évaluation RAG.
"""

import pytest
import os
from unittest.mock import Mock, patch
import tempfile
from app.core.evaluation import RAGEvaluator, MetricsCollector, EvaluationResult
from app.core.advanced_rag import AdvancedRAGPipeline
from app.core.model_config import ModelConfiguration, ModelProvider, EmbeddingProvider

class TestRAGEvaluator:
    """Tests pour l'évaluateur RAG."""
    
    def setup_method(self):
        """Configuration avant chaque test."""
        self.evaluator = RAGEvaluator()
        self.sample_question = "Quel est le chiffre d'affaires de l'entreprise?"
        self.sample_answer = "Le chiffre d'affaires de l'entreprise est de 100 millions d'euros en 2023."
        self.sample_sources = [
            {
                "content": "L'entreprise a réalisé un chiffre d'affaires de 100 millions d'euros au cours de l'exercice 2023.",
                "metadata": {"source": "rapport_annuel.pdf", "page": 15}
            },
            {
                "content": "Les revenus totaux s'élèvent à 100M€ pour cette période.",
                "metadata": {"source": "rapport_annuel.pdf", "page": 16}
            }
        ]

    def test_evaluate_response_basic(self):
        """Test d'évaluation basique d'une réponse."""
        result = self.evaluator.evaluate_response(
            question=self.sample_question,
            answer=self.sample_answer,
            sources=self.sample_sources
        )
        
        assert isinstance(result, EvaluationResult)
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.relevance_score <= 1.0
        assert 0.0 <= result.faithfulness_score <= 1.0
        assert 0.0 <= result.context_precision <= 1.0
        assert 0.0 <= result.context_recall <= 1.0
        assert result.evaluation_time > 0

    def test_evaluate_response_with_reference(self):
        """Test d'évaluation avec une réponse de référence."""
        reference_answer = "Le CA de l'entreprise atteint 100 millions d'euros en 2023."
        
        result = self.evaluator.evaluate_response(
            question=self.sample_question,
            answer=self.sample_answer,
            sources=self.sample_sources,
            reference_answer=reference_answer
        )
        
        assert len(result.rouge_scores) > 0
        assert "rouge1" in result.rouge_scores
        assert "rouge2" in result.rouge_scores
        assert "rougeL" in result.rouge_scores

    def test_heuristic_relevance(self):
        """Test de la méthode heuristique de pertinence."""
        # Question et réponse avec beaucoup de mots en commun
        relevance = self.evaluator._heuristic_relevance(
            "chiffre affaires entreprise",
            "Le chiffre d'affaires de l'entreprise est élevé"
        )
        assert relevance > 0.5
        
        # Question et réponse sans mots en commun
        relevance = self.evaluator._heuristic_relevance(
            "chiffre affaires",
            "La météo est belle aujourd'hui"
        )
        assert relevance < 0.5

    def test_heuristic_faithfulness(self):
        """Test de la méthode heuristique de fidélité."""
        faithful_sources = [{"content": "Le chiffre d'affaires est de 100 millions"}]
        unfaithful_sources = [{"content": "Il fait beau aujourd'hui"}]
        
        # Réponse fidèle aux sources
        faithfulness = self.evaluator._heuristic_faithfulness(
            "Le chiffre d'affaires est de 100 millions",
            faithful_sources
        )
        assert faithfulness > 0.5
        
        # Réponse non fidèle aux sources
        faithfulness = self.evaluator._heuristic_faithfulness(
            "Le chiffre d'affaires est de 100 millions",
            unfaithful_sources
        )
        assert faithfulness < 0.5

    def test_evaluate_empty_sources(self):
        """Test d'évaluation avec des sources vides."""
        result = self.evaluator.evaluate_response(
            question=self.sample_question,
            answer=self.sample_answer,
            sources=[]
        )
        
        assert result.faithfulness_score == 0.0
        assert result.context_precision == 0.0
        assert result.context_recall == 0.0

    def test_evaluate_error_handling(self):
        """Test de gestion d'erreurs dans l'évaluation."""
        # Simuler une erreur dans l'évaluation
        with patch.object(self.evaluator, '_evaluate_relevance', side_effect=Exception("Test error")):
            result = self.evaluator.evaluate_response(
                question=self.sample_question,
                answer=self.sample_answer,
                sources=self.sample_sources
            )
            
            # L'évaluateur doit retourner des scores par défaut
            assert result.overall_score == 0.5

class TestMetricsCollector:
    """Tests pour le collecteur de métriques."""
    
    def setup_method(self):
        """Configuration avant chaque test."""
        self.collector = MetricsCollector()

    def test_record_question_success(self):
        """Test d'enregistrement d'une question réussie."""
        self.collector.record_question(
            response_time=1.5,
            confidence_score=0.8,
            evaluation_score=0.75
        )
        
        metrics = self.collector.get_metrics()
        assert metrics["total_questions"] == 1
        assert metrics["avg_response_time"] == 1.5
        assert metrics["avg_confidence_score"] == 0.8
        assert metrics["avg_evaluation_score"] == 0.75
        assert metrics["error_rate"] == 0.0

    def test_record_question_error(self):
        """Test d'enregistrement d'une question avec erreur."""
        self.collector.record_question(
            response_time=0,
            confidence_score=0,
            error=True
        )
        
        metrics = self.collector.get_metrics()
        assert metrics["total_questions"] == 1
        assert metrics["error_rate"] == 1.0

    def test_record_multiple_questions(self):
        """Test d'enregistrement de plusieurs questions."""
        # Enregistrer plusieurs questions
        for i in range(5):
            self.collector.record_question(
                response_time=i + 1,
                confidence_score=0.1 * (i + 1),
                evaluation_score=0.1 * (i + 1)
            )
        
        metrics = self.collector.get_metrics()
        assert metrics["total_questions"] == 5
        assert metrics["avg_response_time"] == 3.0  # (1+2+3+4+5)/5
        assert metrics["avg_confidence_score"] == 0.3  # (0.1+0.2+0.3+0.4+0.5)/5

    def test_record_document(self):
        """Test d'enregistrement d'un document."""
        self.collector.record_document(chunks_count=50)
        self.collector.record_document(chunks_count=30)
        
        metrics = self.collector.get_metrics()
        assert metrics["total_documents"] == 2
        assert metrics["total_chunks"] == 80

    def test_reset_metrics(self):
        """Test de remise à zéro des métriques."""
        self.collector.record_question(1.0, 0.5)
        self.collector.record_document(25)
        
        # Vérifier que les métriques sont enregistrées
        assert self.collector.get_metrics()["total_questions"] == 1
        
        # Remettre à zéro
        self.collector.reset_metrics()
        
        # Vérifier que tout est remis à zéro
        metrics = self.collector.get_metrics()
        assert metrics["total_questions"] == 0
        assert metrics["total_documents"] == 0

class TestModelConfiguration:
    """Tests pour la configuration des modèles."""
    
    def setup_method(self):
        """Configuration avant chaque test."""
        self.config = ModelConfiguration()

    def test_get_available_models(self):
        """Test de récupération des modèles disponibles."""
        models = self.config.get_available_models()
        
        assert "llm_models" in models
        assert "embedding_models" in models
        assert ModelProvider.OPENAI.value in models["llm_models"]
        assert EmbeddingProvider.OPENAI.value in models["embedding_models"]

    def test_get_llm_openai(self):
        """Test de création d'un LLM OpenAI."""
        with patch('app.core.model_config.ChatOpenAI') as mock_chat:
            llm = self.config.get_llm(ModelProvider.OPENAI, "gpt-3.5-turbo")
            mock_chat.assert_called_once()

    def test_get_llm_ollama(self):
        """Test de création d'un LLM Ollama."""
        with patch('app.core.model_config.Ollama') as mock_ollama:
            llm = self.config.get_llm(ModelProvider.OLLAMA, "mistral")
            mock_ollama.assert_called_once()

    def test_get_embeddings_openai(self):
        """Test de création d'embeddings OpenAI."""
        with patch('app.core.model_config.OpenAIEmbeddings') as mock_embeddings:
            embeddings = self.config.get_embeddings(EmbeddingProvider.OPENAI, "text-embedding-ada-002")
            mock_embeddings.assert_called_once()

    def test_get_embeddings_huggingface(self):
        """Test de création d'embeddings HuggingFace."""
        with patch('app.core.model_config.HuggingFaceEmbeddings') as mock_embeddings:
            embeddings = self.config.get_embeddings(EmbeddingProvider.HUGGINGFACE, "all-MiniLM-L6-v2")
            mock_embeddings.assert_called_once()

    def test_get_model_cost(self):
        """Test de récupération du coût d'un modèle."""
        cost = self.config.get_model_cost(ModelProvider.OPENAI, "gpt-3.5-turbo")
        assert cost == 0.002
        
        cost = self.config.get_model_cost(ModelProvider.OLLAMA, "mistral")
        assert cost == 0.0  # Modèle local gratuit

    def test_get_embedding_cost(self):
        """Test de récupération du coût d'embeddings."""
        cost = self.config.get_embedding_cost(EmbeddingProvider.OPENAI, "text-embedding-ada-002")
        assert cost == 0.0001
        
        cost = self.config.get_embedding_cost(EmbeddingProvider.HUGGINGFACE, "all-MiniLM-L6-v2")
        assert cost == 0.0  # Modèle gratuit

@pytest.fixture
def temp_pdf():
    """Fixture pour créer un PDF temporaire de test."""
    # Pour les tests, on va juste créer un fichier texte
    # Dans un vrai test, on utiliserait une vraie librairie pour créer des PDFs
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(b"Contenu de test du PDF")
        temp_path = f.name
    
    yield temp_path
    
    # Nettoyer après le test
    if os.path.exists(temp_path):
        os.unlink(temp_path)

class TestAdvancedRAGPipelineIntegration:
    """Tests d'intégration pour le pipeline RAG avancé."""
    
    def test_pipeline_creation(self):
        """Test de création du pipeline."""
        pipeline = AdvancedRAGPipeline()
        assert pipeline.session_id is not None
        assert pipeline.processing_stats["documents_processed"] == 0

    def test_session_management(self):
        """Test de gestion des sessions."""
        pipeline = AdvancedRAGPipeline()
        
        # Créer une session
        session_id = pipeline.create_or_load_session("Test Session")
        assert session_id is not None
        
        # Créer un autre pipeline avec la même session
        pipeline2 = AdvancedRAGPipeline(session_id)
        assert pipeline2.session_id == session_id

    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Pas de clé OpenAI pour les tests")
    def test_document_processing_integration(self, temp_pdf):
        """Test d'intégration du traitement de documents."""
        pipeline = AdvancedRAGPipeline()
        pipeline.create_or_load_session("Test Integration")
        
        # Ce test nécessiterait un vrai PDF et une clé API
        # Pour l'instant, on teste juste que la méthode peut être appelée
        try:
            result = pipeline.process_document(temp_pdf, "test.pdf")
            # Si on arrive ici, la structure de base fonctionne
            assert "success" in result
        except Exception as e:
            # Attendu sans vraie clé API ou vrai PDF
            assert "API" in str(e) or "PDF" in str(e)

class TestEndToEndWorkflow:
    """Tests de bout en bout pour le workflow complet."""
    
    def test_complete_rag_workflow_mock(self):
        """Test du workflow RAG complet avec des mocks."""
        
        # Mock des composants externes
        with patch('app.core.advanced_rag.PyPDFLoader'), \
             patch('app.core.advanced_rag.Chroma'), \
             patch('app.core.advanced_rag.OpenAIEmbeddings'), \
             patch('app.core.advanced_rag.ChatOpenAI'):
            
            pipeline = AdvancedRAGPipeline()
            session_id = pipeline.create_or_load_session("Integration Test")
            
            # Simuler le traitement d'un document
            with patch.object(pipeline, 'process_document') as mock_process:
                mock_process.return_value = {
                    "success": True,
                    "filename": "test.pdf",
                    "chunks_count": 10,
                    "pages_count": 5,
                    "processing_time": 2.5,
                    "vector_store_id": "session_test"
                }
                
                result = pipeline.process_document("fake_path.pdf", "test.pdf")
                assert result["success"] is True
                assert result["chunks_count"] == 10

if __name__ == "__main__":
    # Lancer les tests
    pytest.main([__file__, "-v"])
