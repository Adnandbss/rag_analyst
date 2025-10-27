"""
Système d'évaluation avancé pour les réponses RAG.
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog
from rouge_score import rouge_scorer
import json
from datetime import datetime

logger = structlog.get_logger(__name__)

@dataclass
class EvaluationResult:
    """Résultat d'évaluation d'une réponse RAG."""
    relevance_score: float
    faithfulness_score: float
    context_precision: float
    context_recall: float
    rouge_scores: Dict[str, float]
    overall_score: float
    evaluation_time: float
    timestamp: datetime

class RAGEvaluator:
    """Évaluateur de qualité pour les réponses RAG."""
    
    def __init__(self, llm_evaluator=None):
        self.rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        self.llm_evaluator = llm_evaluator  # LLM pour évaluation sémantique
        
        # Prompts d'évaluation
        self.relevance_prompt = """
        Évaluez la pertinence de cette réponse par rapport à la question sur une échelle de 0 à 1.
        
        Question: {question}
        Réponse: {answer}
        
        Critères:
        - La réponse adresse-t-elle directement la question?
        - Les informations sont-elles pertinentes?
        - Y a-t-il des informations hors sujet?
        
        Répondez uniquement par un nombre entre 0 et 1:
        """
        
        self.faithfulness_prompt = """
        Évaluez la fidélité de cette réponse par rapport aux sources fournies sur une échelle de 0 à 1.
        
        Réponse: {answer}
        Sources: {sources}
        
        Critères:
        - La réponse est-elle supportée par les sources?
        - Y a-t-il des hallucinations ou inventions?
        - Les faits sont-ils corrects par rapport aux sources?
        
        Répondez uniquement par un nombre entre 0 et 1:
        """

    def evaluate_response(self, 
                         question: str, 
                         answer: str, 
                         sources: List[Dict], 
                         reference_answer: str = None) -> EvaluationResult:
        """
        Évalue une réponse RAG selon plusieurs métriques.
        """
        start_time = time.time()
        
        logger.info("Starting response evaluation", question_length=len(question), answer_length=len(answer))
        
        try:
            # 1. Évaluation de la pertinence
            relevance_score = self._evaluate_relevance(question, answer)
            
            # 2. Évaluation de la fidélité aux sources
            faithfulness_score = self._evaluate_faithfulness(answer, sources)
            
            # 3. Précision et rappel du contexte
            context_precision, context_recall = self._evaluate_context_quality(question, sources)
            
            # 4. Scores ROUGE (si réponse de référence disponible)
            rouge_scores = {}
            if reference_answer:
                rouge_scores = self._calculate_rouge_scores(answer, reference_answer)
            
            # 5. Score global pondéré
            overall_score = self._calculate_overall_score(
                relevance_score, faithfulness_score, context_precision, context_recall
            )
            
            evaluation_time = time.time() - start_time
            
            result = EvaluationResult(
                relevance_score=relevance_score,
                faithfulness_score=faithfulness_score,
                context_precision=context_precision,
                context_recall=context_recall,
                rouge_scores=rouge_scores,
                overall_score=overall_score,
                evaluation_time=evaluation_time,
                timestamp=datetime.utcnow()
            )
            
            logger.info("Response evaluation completed", 
                       overall_score=overall_score,
                       evaluation_time=evaluation_time)
            
            return result
            
        except Exception as e:
            logger.error("Response evaluation failed", error=str(e))
            # Retourner des scores par défaut en cas d'erreur
            return EvaluationResult(
                relevance_score=0.5,
                faithfulness_score=0.5,
                context_precision=0.5,
                context_recall=0.5,
                rouge_scores={},
                overall_score=0.5,
                evaluation_time=time.time() - start_time,
                timestamp=datetime.utcnow()
            )

    def _evaluate_relevance(self, question: str, answer: str) -> float:
        """Évalue la pertinence de la réponse par rapport à la question."""
        if not self.llm_evaluator:
            # Méthode heuristique simple
            return self._heuristic_relevance(question, answer)
        
        try:
            prompt = self.relevance_prompt.format(question=question, answer=answer)
            result = self.llm_evaluator.invoke(prompt)
            
            # Extraire le score numérique
            score_str = result.strip()
            score = float(score_str)
            return max(0.0, min(1.0, score))  # Clamp entre 0 et 1
            
        except Exception as e:
            logger.warning("LLM relevance evaluation failed, using heuristic", error=str(e))
            return self._heuristic_relevance(question, answer)

    def _evaluate_faithfulness(self, answer: str, sources: List[Dict]) -> float:
        """Évalue la fidélité de la réponse aux sources."""
        if not sources:
            return 0.0
            
        if not self.llm_evaluator:
            return self._heuristic_faithfulness(answer, sources)
        
        try:
            sources_text = "\n".join([src.get("content", "") for src in sources])
            prompt = self.faithfulness_prompt.format(answer=answer, sources=sources_text)
            
            result = self.llm_evaluator.invoke(prompt)
            score_str = result.strip()
            score = float(score_str)
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.warning("LLM faithfulness evaluation failed, using heuristic", error=str(e))
            return self._heuristic_faithfulness(answer, sources)

    def _evaluate_context_quality(self, question: str, sources: List[Dict]) -> tuple:
        """Évalue la précision et le rappel du contexte récupéré."""
        if not sources:
            return 0.0, 0.0
        
        # Méthode simple basée sur la présence de mots-clés
        question_words = set(question.lower().split())
        
        relevant_sources = 0
        total_relevance = 0
        
        for source in sources:
            content = source.get("content", "").lower()
            content_words = set(content.split())
            
            # Intersection des mots
            overlap = len(question_words.intersection(content_words))
            if overlap > 0:
                relevant_sources += 1
                total_relevance += overlap / len(question_words)
        
        precision = relevant_sources / len(sources) if sources else 0
        recall = total_relevance / len(sources) if sources else 0
        
        return precision, recall

    def _calculate_rouge_scores(self, answer: str, reference: str) -> Dict[str, float]:
        """Calcule les scores ROUGE par rapport à une réponse de référence."""
        try:
            scores = self.rouge_scorer.score(reference, answer)
            return {
                'rouge1': scores['rouge1'].fmeasure,
                'rouge2': scores['rouge2'].fmeasure,
                'rougeL': scores['rougeL'].fmeasure
            }
        except Exception as e:
            logger.warning("ROUGE calculation failed", error=str(e))
            return {}

    def _calculate_overall_score(self, relevance: float, faithfulness: float, 
                               precision: float, recall: float) -> float:
        """Calcule un score global pondéré."""
        weights = {
            'relevance': 0.4,
            'faithfulness': 0.3,
            'precision': 0.15,
            'recall': 0.15
        }
        
        return (
            weights['relevance'] * relevance +
            weights['faithfulness'] * faithfulness +
            weights['precision'] * precision +
            weights['recall'] * recall
        )

    def _heuristic_relevance(self, question: str, answer: str) -> float:
        """Méthode heuristique pour évaluer la pertinence."""
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        if not question_words:
            return 0.0
        
        overlap = len(question_words.intersection(answer_words))
        return min(1.0, overlap / len(question_words))

    def _heuristic_faithfulness(self, answer: str, sources: List[Dict]) -> float:
        """Méthode heuristique pour évaluer la fidélité."""
        if not sources:
            return 0.0
        
        answer_words = set(answer.lower().split())
        source_words = set()
        
        for source in sources:
            content = source.get("content", "").lower()
            source_words.update(content.split())
        
        if not answer_words:
            return 1.0
        
        overlap = len(answer_words.intersection(source_words))
        return overlap / len(answer_words)

class MetricsCollector:
    """Collecteur de métriques pour monitoring."""
    
    def __init__(self):
        self.metrics = {
            "total_questions": 0,
            "avg_response_time": 0.0,
            "avg_confidence_score": 0.0,
            "avg_evaluation_score": 0.0,
            "error_rate": 0.0,
            "total_documents": 0,
            "total_chunks": 0
        }
        self.response_times = []
        self.confidence_scores = []
        self.evaluation_scores = []
        self.error_count = 0

    def record_question(self, response_time: float, confidence_score: float, 
                       evaluation_score: float = None, error: bool = False):
        """Enregistre les métriques d'une question."""
        self.metrics["total_questions"] += 1
        
        if error:
            self.error_count += 1
        else:
            self.response_times.append(response_time)
            self.confidence_scores.append(confidence_score)
            
            if evaluation_score:
                self.evaluation_scores.append(evaluation_score)
        
        # Mettre à jour les moyennes
        self._update_averages()

    def record_document(self, chunks_count: int):
        """Enregistre l'ajout d'un document."""
        self.metrics["total_documents"] += 1
        self.metrics["total_chunks"] += chunks_count

    def _update_averages(self):
        """Met à jour les moyennes calculées."""
        if self.response_times:
            self.metrics["avg_response_time"] = sum(self.response_times) / len(self.response_times)
        
        if self.confidence_scores:
            self.metrics["avg_confidence_score"] = sum(self.confidence_scores) / len(self.confidence_scores)
        
        if self.evaluation_scores:
            self.metrics["avg_evaluation_score"] = sum(self.evaluation_scores) / len(self.evaluation_scores)
        
        if self.metrics["total_questions"] > 0:
            self.metrics["error_rate"] = self.error_count / self.metrics["total_questions"]

    def get_metrics(self) -> Dict[str, Any]:
        """Retourne toutes les métriques collectées."""
        return self.metrics.copy()

    def reset_metrics(self):
        """Remet à zéro toutes les métriques."""
        self.__init__()

# Instance globale du collecteur de métriques
global_metrics = MetricsCollector()
