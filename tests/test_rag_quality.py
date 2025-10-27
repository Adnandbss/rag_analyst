"""
Tests automatisés de qualité pour le système RAG.
Ces tests vérifient que le système RAG maintient un niveau de qualité acceptable.
"""

import pytest
import os
import json
from unittest.mock import Mock, patch
from pathlib import Path

from app.core.rag_evaluation_suite import (
    RAGEvaluationSuite,
    TestCase,
    TestResult
)
from app.core.advanced_rag import AdvancedRAGPipeline


class TestRAGEvaluationSuite:
    """Tests pour la suite d'évaluation RAG."""
    
    def setup_method(self):
        """Configuration avant chaque test."""
        self.evaluation_suite = RAGEvaluationSuite()

    def test_suite_initialization(self):
        """Test d'initialisation de la suite."""
        assert self.evaluation_suite is not None
        assert len(self.evaluation_suite.test_cases) > 0
        assert self.evaluation_suite.evaluator is not None

    def test_default_test_cases(self):
        """Test de création des test cases par défaut."""
        test_cases = self.evaluation_suite._create_default_test_cases()
        
        assert len(test_cases) >= 5
        assert all(isinstance(tc, TestCase) for tc in test_cases)
        assert all(tc.id.startswith("TC") for tc in test_cases)
        assert all(tc.question for tc in test_cases)

    def test_load_test_cases_from_file(self):
        """Test de chargement des test cases depuis un fichier."""
        # Créer un fichier de test temporaire
        test_data = {
            "test_cases": [
                {
                    "id": "TEST001",
                    "question": "Test question ?",
                    "expected_answer": "Test answer",
                    "category": "test",
                    "difficulty": "easy",
                    "tags": ["test"]
                }
            ]
        }
        
        test_file = "test_cases_temp.json"
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        try:
            suite = RAGEvaluationSuite(test_file)
            assert len(suite.test_cases) == 1
            assert suite.test_cases[0].id == "TEST001"
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_run_single_test_mock(self):
        """Test d'exécution d'un test case avec mock."""
        test_case = TestCase(
            id="MOCK001",
            question="Test question?",
            expected_answer="Test answer",
            category="test"
        )
        
        # Mock du pipeline RAG
        mock_pipeline = Mock()
        mock_pipeline.ask_question.return_value = {
            "answer": "Test answer from RAG",
            "sources": [{"content": "Test source"}],
            "response_time": 1.0,
            "confidence_score": 0.8
        }
        
        # Mock de l'évaluateur
        with patch.object(self.evaluation_suite.evaluator, 'evaluate_response') as mock_eval:
            mock_eval_result = Mock()
            mock_eval_result.overall_score = 0.85
            mock_eval_result.relevance_score = 0.9
            mock_eval_result.faithfulness_score = 0.8
            mock_eval_result.context_precision = 0.85
            mock_eval_result.context_recall = 0.8
            mock_eval.return_value = mock_eval_result
            
            result = self.evaluation_suite._run_single_test(mock_pipeline, test_case)
            
            assert isinstance(result, TestResult)
            assert result.test_case_id == "MOCK001"
            assert result.passed is True  # Score > 0.6
            assert result.answer == "Test answer from RAG"

    def test_generate_summary(self):
        """Test de génération du résumé."""
        # Créer des résultats fictifs
        self.evaluation_suite.results = [
            TestResult(
                test_case_id="TC001",
                question="Q1",
                answer="A1",
                expected_answer=None,
                evaluation_scores={"overall": 0.8, "relevance": 0.9},
                passed=True,
                response_time=1.0,
                timestamp="2024-01-01T00:00:00"
            ),
            TestResult(
                test_case_id="TC002",
                question="Q2",
                answer="A2",
                expected_answer=None,
                evaluation_scores={"overall": 0.5, "relevance": 0.6},
                passed=False,
                response_time=1.5,
                timestamp="2024-01-01T00:00:01"
            )
        ]
        
        summary = self.evaluation_suite._generate_summary(10.0)
        
        assert summary["total_tests"] == 2
        assert summary["passed_count"] == 1
        assert summary["failed_count"] == 1
        assert summary["pass_rate"] == 0.5
        assert "average_scores" in summary
        assert summary["avg_response_time"] == 1.25

    def test_get_results_by_category(self):
        """Test de regroupement des résultats par catégorie."""
        # Ajouter des test cases
        self.evaluation_suite.test_cases = [
            TestCase(id="TC001", question="Q1", category="cat1"),
            TestCase(id="TC002", question="Q2", category="cat1"),
            TestCase(id="TC003", question="Q3", category="cat2")
        ]
        
        # Ajouter des résultats
        self.evaluation_suite.results = [
            TestResult("TC001", "Q1", "A1", None, {}, True, timestamp="2024-01-01T00:00:00"),
            TestResult("TC002", "Q2", "A2", None, {}, True, timestamp="2024-01-01T00:00:00"),
            TestResult("TC003", "Q3", "A3", None, {}, False, timestamp="2024-01-01T00:00:00")
        ]
        
        by_category = self.evaluation_suite.get_results_by_category()
        
        assert "cat1" in by_category
        assert "cat2" in by_category
        assert len(by_category["cat1"]) == 2
        assert len(by_category["cat2"]) == 1

    def test_failed_tests_analysis(self):
        """Test d'analyse des tests échoués."""
        # Créer des résultats avec échecs
        self.evaluation_suite.results = [
            TestResult(
                "TC001", "Q1", "A1", None,
                {"overall": 0.4, "relevance": 0.3, "faithfulness": 0.5},
                False,
                timestamp="2024-01-01T00:00:00"
            ),
            TestResult(
                "TC002", "Q2", "A2", None,
                {"overall": 0.5, "relevance": 0.7, "faithfulness": 0.3},
                False,
                timestamp="2024-01-01T00:00:00"
            )
        ]
        
        analysis = self.evaluation_suite.get_failed_tests_analysis()
        
        assert analysis["failed_count"] == 2
        assert "problematic_metrics" in analysis
        assert "recommendations" in analysis
        assert len(analysis["recommendations"]) > 0

    def test_export_results_json(self):
        """Test d'export des résultats en JSON."""
        # Ajouter des résultats
        self.evaluation_suite.results = [
            TestResult("TC001", "Q1", "A1", None, {"overall": 0.8}, True, timestamp="2024-01-01T00:00:00")
        ]
        
        output_file = "test_export.json"
        
        try:
            filepath = self.evaluation_suite.export_results_json(output_file)
            
            assert os.path.exists(filepath)
            
            # Vérifier le contenu
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert "summary" in data
            assert "test_results" in data
            assert "generated_at" in data
            
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    @pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"), 
                       reason="Tests d'intégration désactivés par défaut")
    def test_full_evaluation_integration(self):
        """Test d'intégration complet de l'évaluation."""
        # Ce test nécessite un vrai pipeline RAG avec des documents
        # Il est skippé par défaut
        pass


class TestQualityThresholds:
    """Tests pour vérifier que le système maintient des seuils de qualité."""
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), 
                       reason="Pas de clé OpenAI")
    def test_minimum_quality_threshold(self):
        """Vérifie que le score moyen est au-dessus du seuil minimal."""
        MINIMUM_ACCEPTABLE_SCORE = 0.6
        
        # Ce test devrait être exécuté en CI/CD avec un dataset connu
        # Pour l'instant, c'est un placeholder
        pass

    def test_response_time_threshold(self):
        """Vérifie que les temps de réponse sont acceptables."""
        MAXIMUM_RESPONSE_TIME = 10.0  # secondes
        
        # Ce test devrait mesurer les temps de réponse réels
        pass


if __name__ == "__main__":
    # Lancer les tests
    pytest.main([__file__, "-v", "--tb=short"])

