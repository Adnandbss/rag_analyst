"""
Suite complète de tests d'évaluation pour les systèmes RAG.
Mesure la qualité des réponses avec des métriques standard de l'industrie.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json
import time
from datetime import datetime
import structlog
from pathlib import Path

from app.core.evaluation import RAGEvaluator, EvaluationResult

logger = structlog.get_logger(__name__)

@dataclass
class TestCase:
    """Un cas de test pour l'évaluation RAG."""
    id: str
    question: str
    expected_answer: Optional[str] = None
    context_documents: List[str] = None
    category: str = "general"
    difficulty: str = "medium"  # easy, medium, hard
    tags: List[str] = None

@dataclass
class TestResult:
    """Résultat d'un test."""
    test_case_id: str
    question: str
    answer: str
    expected_answer: Optional[str]
    evaluation_scores: Dict[str, float]
    passed: bool
    error: Optional[str] = None
    response_time: float = 0.0
    timestamp: str = None

class RAGEvaluationSuite:
    """Suite de tests complète pour évaluer un système RAG."""
    
    def __init__(self, test_cases_file: str = None):
        """
        Initialise la suite de tests.
        
        Args:
            test_cases_file: Chemin vers le fichier JSON contenant les test cases
        """
        self.evaluator = RAGEvaluator()
        self.test_cases = []
        self.results = []
        
        if test_cases_file and Path(test_cases_file).exists():
            self.load_test_cases(test_cases_file)
        else:
            # Créer des test cases par défaut
            self.test_cases = self._create_default_test_cases()
        
        logger.info("RAG Evaluation Suite initialized", 
                   test_cases_count=len(self.test_cases))

    def load_test_cases(self, filepath: str):
        """Charge les test cases depuis un fichier JSON."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self.test_cases = [
                TestCase(**tc) for tc in data.get("test_cases", [])
            ]
            
            logger.info("Test cases loaded", 
                       filepath=filepath,
                       count=len(self.test_cases))
            
        except Exception as e:
            logger.error("Failed to load test cases", 
                        filepath=filepath,
                        error=str(e))
            raise

    def _create_default_test_cases(self) -> List[TestCase]:
        """Crée des test cases par défaut pour la démonstration."""
        return [
            TestCase(
                id="TC001",
                question="Quel est le chiffre d'affaires de l'entreprise en 2023 ?",
                expected_answer="Le chiffre d'affaires est de 100 millions d'euros.",
                category="financial_analysis",
                difficulty="easy",
                tags=["finances", "CA", "2023"]
            ),
            TestCase(
                id="TC002",
                question="Quels sont les trois principaux risques mentionnés dans le rapport ?",
                expected_answer=None,  # Pas de réponse attendue stricte
                category="risk_analysis",
                difficulty="medium",
                tags=["risques", "analyse"]
            ),
            TestCase(
                id="TC003",
                question="Compare les performances financières de 2022 et 2023.",
                expected_answer=None,
                category="comparative_analysis",
                difficulty="hard",
                tags=["comparaison", "évolution", "finances"]
            ),
            TestCase(
                id="TC004",
                question="Quelle est la stratégie de l'entreprise pour les 3 prochaines années ?",
                expected_answer=None,
                category="strategic_analysis",
                difficulty="medium",
                tags=["stratégie", "futur"]
            ),
            TestCase(
                id="TC005",
                question="L'entreprise a-t-elle des partenariats internationaux ?",
                expected_answer=None,
                category="partnerships",
                difficulty="easy",
                tags=["partenariats", "international"]
            )
        ]

    def run_evaluation(self, rag_pipeline, test_cases: List[TestCase] = None) -> Dict[str, Any]:
        """
        Exécute l'évaluation complète sur tous les test cases.
        
        Args:
            rag_pipeline: Pipeline RAG à évaluer
            test_cases: Liste de test cases (utilise self.test_cases si None)
            
        Returns:
            Dictionnaire avec les résultats détaillés
        """
        cases_to_test = test_cases or self.test_cases
        
        logger.info("Starting RAG evaluation", test_cases_count=len(cases_to_test))
        
        start_time = time.time()
        self.results = []
        
        for i, test_case in enumerate(cases_to_test, 1):
            logger.info(f"Running test case {i}/{len(cases_to_test)}", 
                       test_id=test_case.id,
                       question=test_case.question[:50])
            
            result = self._run_single_test(rag_pipeline, test_case)
            self.results.append(result)
        
        total_time = time.time() - start_time
        
        # Calculer les statistiques globales
        summary = self._generate_summary(total_time)
        
        logger.info("RAG evaluation completed",
                   total_tests=len(cases_to_test),
                   passed=summary["passed_count"],
                   failed=summary["failed_count"],
                   total_time=total_time)
        
        return {
            "summary": summary,
            "test_results": [asdict(r) for r in self.results],
            "generated_at": datetime.utcnow().isoformat()
        }

    def _run_single_test(self, rag_pipeline, test_case: TestCase) -> TestResult:
        """Exécute un test case unique."""
        test_start = time.time()
        
        try:
            # Poser la question au système RAG
            result = rag_pipeline.ask_question(test_case.question, save_conversation=False)
            
            answer = result["answer"]
            sources = result.get("sources", [])
            response_time = time.time() - test_start
            
            # Évaluer la réponse
            eval_result = self.evaluator.evaluate_response(
                question=test_case.question,
                answer=answer,
                sources=sources,
                reference_answer=test_case.expected_answer
            )
            
            # Déterminer si le test passe
            # Un test passe si le score global est > 0.6
            passed = eval_result.overall_score >= 0.6
            
            return TestResult(
                test_case_id=test_case.id,
                question=test_case.question,
                answer=answer,
                expected_answer=test_case.expected_answer,
                evaluation_scores={
                    "overall": eval_result.overall_score,
                    "relevance": eval_result.relevance_score,
                    "faithfulness": eval_result.faithfulness_score,
                    "context_precision": eval_result.context_precision,
                    "context_recall": eval_result.context_recall
                },
                passed=passed,
                response_time=response_time,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error("Test execution failed",
                        test_id=test_case.id,
                        error=str(e))
            
            return TestResult(
                test_case_id=test_case.id,
                question=test_case.question,
                answer="",
                expected_answer=test_case.expected_answer,
                evaluation_scores={},
                passed=False,
                error=str(e),
                response_time=time.time() - test_start,
                timestamp=datetime.utcnow().isoformat()
            )

    def _generate_summary(self, total_time: float) -> Dict[str, Any]:
        """Génère un résumé des résultats."""
        if not self.results:
            return {}
        
        passed_results = [r for r in self.results if r.passed]
        failed_results = [r for r in self.results if not r.passed]
        
        # Scores moyens
        all_scores = [r.evaluation_scores for r in self.results if r.evaluation_scores]
        
        avg_scores = {}
        if all_scores:
            for key in ["overall", "relevance", "faithfulness", "context_precision", "context_recall"]:
                scores = [s.get(key, 0) for s in all_scores if key in s]
                avg_scores[key] = sum(scores) / len(scores) if scores else 0
        
        # Temps de réponse
        response_times = [r.response_time for r in self.results if r.response_time]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_tests": len(self.results),
            "passed_count": len(passed_results),
            "failed_count": len(failed_results),
            "pass_rate": len(passed_results) / len(self.results) if self.results else 0,
            "average_scores": avg_scores,
            "avg_response_time": avg_response_time,
            "total_evaluation_time": total_time,
            "failed_test_ids": [r.test_case_id for r in failed_results]
        }

    def generate_html_report(self, output_file: str = "evaluation_report.html"):
        """Génère un rapport HTML des résultats."""
        if not self.results:
            logger.warning("No results to generate report")
            return None
        
        summary = self._generate_summary(0)
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>RAG Evaluation Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 20px; margin: 30px 0; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 8px; 
                       box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .test-result {{ background: white; margin: 15px 0; padding: 20px; 
                       border-radius: 8px; border-left: 4px solid #667eea; }}
        .passed {{ border-left-color: #48bb78; }}
        .failed {{ border-left-color: #f56565; }}
        .scores {{ display: flex; gap: 15px; margin: 10px 0; flex-wrap: wrap; }}
        .score-badge {{ padding: 8px 15px; border-radius: 5px; font-weight: bold; }}
        .score-excellent {{ background: #c6f6d5; color: #22543d; }}
        .score-good {{ background: #bee3f8; color: #2c5282; }}
        .score-average {{ background: #feebc8; color: #7c2d12; }}
        .score-poor {{ background: #fed7d7; color: #742a2a; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 RAG Evaluation Report</h1>
        <p>Généré le : {generated_at}</p>
    </div>
    
    <div class="summary">
        <div class="metric-card">
            <div class="metric-value">{total_tests}</div>
            <div>Tests Exécutés</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color: #48bb78;">{passed}</div>
            <div>Tests Réussis</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color: #f56565;">{failed}</div>
            <div>Tests Échoués</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{pass_rate:.1%}</div>
            <div>Taux de Réussite</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{avg_score:.2f}</div>
            <div>Score Moyen</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{avg_time:.2f}s</div>
            <div>Temps Moyen</div>
        </div>
    </div>
    
    <h2>Résultats Détaillés</h2>
    {test_results_html}
    
</body>
</html>
"""
        
        # Générer le HTML des résultats
        test_results_html = ""
        for result in self.results:
            status_class = "passed" if result.passed else "failed"
            status_icon = "✅" if result.passed else "❌"
            
            scores_html = ""
            if result.evaluation_scores:
                for metric, score in result.evaluation_scores.items():
                    score_class = self._get_score_class_name(score)
                    scores_html += f'<span class="score-badge {score_class}">{metric}: {score:.2f}</span>'
            
            test_results_html += f"""
            <div class="test-result {status_class}">
                <h3>{status_icon} Test {result.test_case_id}</h3>
                <p><strong>Question:</strong> {result.question}</p>
                <p><strong>Réponse:</strong> {result.answer[:300]}...</p>
                {f'<p><strong>Réponse attendue:</strong> {result.expected_answer}</p>' if result.expected_answer else ''}
                <div class="scores">{scores_html}</div>
                <p><em>Temps de réponse: {result.response_time:.2f}s</em></p>
                {f'<p style="color: #f56565;"><strong>Erreur:</strong> {result.error}</p>' if result.error else ''}
            </div>
            """
        
        # Remplir le template
        html_content = html_template.format(
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            total_tests=summary["total_tests"],
            passed=summary["passed_count"],
            failed=summary["failed_count"],
            pass_rate=summary["pass_rate"],
            avg_score=summary["average_scores"].get("overall", 0),
            avg_time=summary["avg_response_time"],
            test_results_html=test_results_html
        )
        
        # Sauvegarder le rapport
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info("HTML report generated", filepath=str(output_path))
        return str(output_path)

    def _get_score_class_name(self, score: float) -> str:
        """Retourne le nom de la classe CSS selon le score."""
        if score >= 0.8:
            return "score-excellent"
        elif score >= 0.6:
            return "score-good"
        elif score >= 0.4:
            return "score-average"
        else:
            return "score-poor"

    def export_results_json(self, output_file: str = "evaluation_results.json"):
        """Exporte les résultats en JSON."""
        summary = self._generate_summary(0)
        
        data = {
            "summary": summary,
            "test_results": [asdict(r) for r in self.results],
            "generated_at": datetime.utcnow().isoformat()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info("JSON results exported", filepath=output_file)
        return output_file

    def get_results_by_category(self) -> Dict[str, List[TestResult]]:
        """Regroupe les résultats par catégorie."""
        categories = {}
        
        for result in self.results:
            # Trouver le test case correspondant
            test_case = next((tc for tc in self.test_cases if tc.id == result.test_case_id), None)
            
            if test_case:
                category = test_case.category
                if category not in categories:
                    categories[category] = []
                categories[category].append(result)
        
        return categories

    def get_failed_tests_analysis(self) -> Dict[str, Any]:
        """Analyse les tests échoués pour identifier les patterns."""
        failed = [r for r in self.results if not r.passed]
        
        if not failed:
            return {"message": "Aucun test échoué", "failed_count": 0}
        
        # Analyser les causes d'échec
        error_types = {}
        low_score_metrics = {"relevance": 0, "faithfulness": 0, "precision": 0, "recall": 0}
        
        for result in failed:
            if result.error:
                error_type = type(result.error).__name__
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if result.evaluation_scores:
                if result.evaluation_scores.get("relevance", 1) < 0.6:
                    low_score_metrics["relevance"] += 1
                if result.evaluation_scores.get("faithfulness", 1) < 0.6:
                    low_score_metrics["faithfulness"] += 1
                if result.evaluation_scores.get("context_precision", 1) < 0.6:
                    low_score_metrics["precision"] += 1
                if result.evaluation_scores.get("context_recall", 1) < 0.6:
                    low_score_metrics["recall"] += 1
        
        # Recommandations
        recommendations = []
        if low_score_metrics["relevance"] > len(failed) / 2:
            recommendations.append("Améliorer la pertinence : revoir le prompt système ou le modèle")
        if low_score_metrics["faithfulness"] > len(failed) / 2:
            recommendations.append("Réduire les hallucinations : ajuster la température, améliorer les sources")
        if low_score_metrics["precision"] > len(failed) / 2:
            recommendations.append("Améliorer la précision du retrieval : ajuster k, revoir le chunking")
        if low_score_metrics["recall"] > len(failed) / 2:
            recommendations.append("Améliorer le rappel : augmenter la taille des chunks, utiliser hybrid search")
        
        return {
            "failed_count": len(failed),
            "error_types": error_types,
            "problematic_metrics": low_score_metrics,
            "recommendations": recommendations
        }

    def compare_with_baseline(self, baseline_file: str) -> Dict[str, Any]:
        """Compare les résultats avec une baseline précédente."""
        try:
            with open(baseline_file, 'r') as f:
                baseline = json.load(f)
            
            current_avg_score = self._generate_summary(0)["average_scores"].get("overall", 0)
            baseline_avg_score = baseline["summary"]["average_scores"].get("overall", 0)
            
            improvement = current_avg_score - baseline_avg_score
            improvement_pct = (improvement / baseline_avg_score * 100) if baseline_avg_score > 0 else 0
            
            return {
                "current_score": current_avg_score,
                "baseline_score": baseline_avg_score,
                "improvement": improvement,
                "improvement_percentage": improvement_pct,
                "better": improvement > 0
            }
            
        except Exception as e:
            logger.error("Baseline comparison failed", error=str(e))
            return {"error": str(e)}

# Instance globale de la suite de tests
evaluation_suite = RAGEvaluationSuite()
