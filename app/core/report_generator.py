"""
Générateur de rapports et analytics avancés pour RAG Analyst.
"""

import json
import csv
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
from jinja2 import Template
import structlog
import os

from app.core.database import (
    get_db, ChatSession, Document, Conversation, EvaluationMetric
)

logger = structlog.get_logger(__name__)

class ReportGenerator:
    """Générateur de rapports d'analyse et de performance."""
    
    def __init__(self):
        self.report_templates = {
            "session_summary": self._get_session_summary_template(),
            "performance_analysis": self._get_performance_template(),
            "evaluation_report": self._get_evaluation_template()
        }

    def generate_session_report(self, session_id: str, format: str = "json") -> Dict[str, Any]:
        """
        Génère un rapport détaillé pour une session spécifique.
        """
        logger.info("Generating session report", session_id=session_id, format=format)
        
        db = next(get_db())
        try:
            # Récupérer les données de la session
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                raise ValueError(f"Session {session_id} not found")

            documents = db.query(Document).filter(Document.session_id == session_id).all()
            conversations = db.query(Conversation).filter(Conversation.session_id == session_id).all()
            
            # Calculer les statistiques
            stats = self._calculate_session_stats(conversations, documents)
            
            # Préparer les données du rapport
            report_data = {
                "session_info": {
                    "id": session.id,
                    "name": session.name,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "is_active": session.is_active
                },
                "documents_summary": {
                    "total_documents": len(documents),
                    "total_pages": sum(doc.pages_count or 0 for doc in documents),
                    "total_chunks": sum(doc.chunks_count or 0 for doc in documents),
                    "avg_processing_time": sum(doc.processing_time or 0 for doc in documents) / max(len(documents), 1),
                    "documents_list": [
                        {
                            "filename": doc.original_name,
                            "pages": doc.pages_count,
                            "chunks": doc.chunks_count,
                            "processing_time": doc.processing_time,
                            "upload_time": doc.upload_time.isoformat()
                        }
                        for doc in documents
                    ]
                },
                "conversations_summary": {
                    "total_conversations": len(conversations),
                    "avg_response_time": stats["avg_response_time"],
                    "avg_confidence_score": stats["avg_confidence_score"],
                    "total_sources_used": sum(conv.sources_count or 0 for conv in conversations),
                    "model_usage": stats["model_usage"],
                    "conversations_timeline": [
                        {
                            "timestamp": conv.timestamp.isoformat(),
                            "question": conv.question[:100] + "..." if len(conv.question) > 100 else conv.question,
                            "response_time": conv.response_time,
                            "confidence_score": conv.confidence_score,
                            "sources_count": conv.sources_count,
                            "model_used": conv.model_used
                        }
                        for conv in conversations[-20:]  # Dernières 20 conversations
                    ]
                },
                "performance_insights": {
                    "best_confidence_score": max((conv.confidence_score for conv in conversations if conv.confidence_score), default=0),
                    "worst_confidence_score": min((conv.confidence_score for conv in conversations if conv.confidence_score), default=0),
                    "fastest_response": min((conv.response_time for conv in conversations if conv.response_time), default=0),
                    "slowest_response": max((conv.response_time for conv in conversations if conv.response_time), default=0),
                    "questions_per_day": stats["questions_per_day"],
                    "peak_usage_hours": stats["peak_hours"]
                },
                "recommendations": self._generate_recommendations(stats, documents, conversations),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            if format == "html":
                return self._generate_html_report(report_data, "session_summary")
            elif format == "csv":
                return self._generate_csv_report(report_data)
            else:
                return report_data
                
        finally:
            db.close()

    def generate_system_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Génère un rapport d'analyse globale du système.
        """
        logger.info("Generating system analytics", days=days)
        
        db = next(get_db())
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Statistiques des sessions
            total_sessions = db.query(ChatSession).count()
            active_sessions = db.query(ChatSession).filter(
                ChatSession.is_active == True,
                ChatSession.last_activity >= cutoff_date
            ).count()
            
            # Statistiques des documents
            total_documents = db.query(Document).count()
            recent_documents = db.query(Document).filter(
                Document.upload_time >= cutoff_date
            ).count()
            
            # Statistiques des conversations
            total_conversations = db.query(Conversation).count()
            recent_conversations = db.query(Conversation).filter(
                Conversation.timestamp >= cutoff_date
            ).all()
            
            # Analyses avancées
            usage_by_day = self._analyze_usage_patterns(db, cutoff_date)
            performance_trends = self._analyze_performance_trends(recent_conversations)
            model_popularity = self._analyze_model_usage(recent_conversations)
            
            return {
                "period": {
                    "start_date": cutoff_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                    "days": days
                },
                "overview": {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "total_documents": total_documents,
                    "recent_documents": recent_documents,
                    "total_conversations": total_conversations,
                    "recent_conversations": len(recent_conversations)
                },
                "usage_patterns": usage_by_day,
                "performance_trends": performance_trends,
                "model_analytics": model_popularity,
                "quality_metrics": self._calculate_quality_metrics(recent_conversations),
                "recommendations": self._generate_system_recommendations(recent_conversations),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()

    def export_session_data(self, session_id: str, format: str = "csv") -> str:
        """
        Exporte les données d'une session dans différents formats.
        """
        logger.info("Exporting session data", session_id=session_id, format=format)
        
        db = next(get_db())
        try:
            conversations = db.query(Conversation).filter(
                Conversation.session_id == session_id
            ).all()
            
            if format == "csv":
                return self._export_to_csv(conversations, session_id)
            elif format == "json":
                return self._export_to_json(conversations, session_id)
            else:
                raise ValueError(f"Format {format} not supported")
                
        finally:
            db.close()

    def _calculate_session_stats(self, conversations: List, documents: List) -> Dict[str, Any]:
        """Calcule les statistiques d'une session."""
        if not conversations:
            return {
                "avg_response_time": 0,
                "avg_confidence_score": 0,
                "model_usage": {},
                "questions_per_day": {},
                "peak_hours": []
            }
        
        # Temps de réponse moyen
        response_times = [conv.response_time for conv in conversations if conv.response_time]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Score de confiance moyen
        confidence_scores = [conv.confidence_score for conv in conversations if conv.confidence_score]
        avg_confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Utilisation des modèles
        model_usage = {}
        for conv in conversations:
            if conv.model_used:
                model_usage[conv.model_used] = model_usage.get(conv.model_used, 0) + 1
        
        # Questions par jour
        questions_per_day = {}
        for conv in conversations:
            day = conv.timestamp.date().isoformat()
            questions_per_day[day] = questions_per_day.get(day, 0) + 1
        
        # Heures de pic
        hours = [conv.timestamp.hour for conv in conversations]
        hour_counts = {}
        for hour in hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        peak_hours = sorted(hour_counts.keys(), key=lambda x: hour_counts[x], reverse=True)[:3]
        
        return {
            "avg_response_time": avg_response_time,
            "avg_confidence_score": avg_confidence_score,
            "model_usage": model_usage,
            "questions_per_day": questions_per_day,
            "peak_hours": peak_hours
        }

    def _analyze_usage_patterns(self, db: Session, cutoff_date: datetime) -> Dict[str, Any]:
        """Analyse les patterns d'utilisation."""
        # Conversations par jour
        daily_conversations = db.query(
            func.date(Conversation.timestamp).label('date'),
            func.count(Conversation.id).label('count')
        ).filter(
            Conversation.timestamp >= cutoff_date
        ).group_by(
            func.date(Conversation.timestamp)
        ).all()
        
        # Documents uploadés par jour
        daily_uploads = db.query(
            func.date(Document.upload_time).label('date'),
            func.count(Document.id).label('count')
        ).filter(
            Document.upload_time >= cutoff_date
        ).group_by(
            func.date(Document.upload_time)
        ).all()
        
        return {
            "daily_conversations": [
                {"date": str(record.date), "count": record.count}
                for record in daily_conversations
            ],
            "daily_uploads": [
                {"date": str(record.date), "count": record.count}
                for record in daily_uploads
            ]
        }

    def _analyze_performance_trends(self, conversations: List) -> Dict[str, Any]:
        """Analyse les tendances de performance."""
        if not conversations:
            return {}
        
        # Trier par timestamp
        conversations = sorted(conversations, key=lambda x: x.timestamp)
        
        # Calculer les moyennes mobiles
        window_size = min(10, len(conversations))
        moving_avg_response_time = []
        moving_avg_confidence = []
        
        for i in range(len(conversations) - window_size + 1):
            window = conversations[i:i+window_size]
            
            response_times = [c.response_time for c in window if c.response_time]
            confidences = [c.confidence_score for c in window if c.confidence_score]
            
            if response_times:
                moving_avg_response_time.append({
                    "timestamp": window[-1].timestamp.isoformat(),
                    "avg_response_time": sum(response_times) / len(response_times)
                })
            
            if confidences:
                moving_avg_confidence.append({
                    "timestamp": window[-1].timestamp.isoformat(),
                    "avg_confidence": sum(confidences) / len(confidences)
                })
        
        return {
            "response_time_trend": moving_avg_response_time,
            "confidence_trend": moving_avg_confidence
        }

    def _analyze_model_usage(self, conversations: List) -> Dict[str, Any]:
        """Analyse l'utilisation des modèles."""
        model_stats = {}
        
        for conv in conversations:
            if not conv.model_used:
                continue
            
            if conv.model_used not in model_stats:
                model_stats[conv.model_used] = {
                    "usage_count": 0,
                    "total_response_time": 0,
                    "total_confidence": 0,
                    "response_times": [],
                    "confidence_scores": []
                }
            
            stats = model_stats[conv.model_used]
            stats["usage_count"] += 1
            
            if conv.response_time:
                stats["total_response_time"] += conv.response_time
                stats["response_times"].append(conv.response_time)
            
            if conv.confidence_score:
                stats["total_confidence"] += conv.confidence_score
                stats["confidence_scores"].append(conv.confidence_score)
        
        # Calculer les moyennes
        for model, stats in model_stats.items():
            if stats["usage_count"] > 0:
                stats["avg_response_time"] = stats["total_response_time"] / stats["usage_count"]
                stats["avg_confidence"] = stats["total_confidence"] / stats["usage_count"]
            
            # Nettoyer les listes temporaires
            del stats["response_times"]
            del stats["confidence_scores"]
            del stats["total_response_time"]
            del stats["total_confidence"]
        
        return model_stats

    def _calculate_quality_metrics(self, conversations: List) -> Dict[str, Any]:
        """Calcule les métriques de qualité."""
        if not conversations:
            return {}
        
        confidence_scores = [c.confidence_score for c in conversations if c.confidence_score]
        response_times = [c.response_time for c in conversations if c.response_time]
        
        return {
            "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "confidence_std": pd.Series(confidence_scores).std() if confidence_scores else 0,
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "response_time_std": pd.Series(response_times).std() if response_times else 0,
            "high_confidence_rate": len([s for s in confidence_scores if s >= 0.8]) / len(confidence_scores) if confidence_scores else 0,
            "fast_response_rate": len([t for t in response_times if t <= 2.0]) / len(response_times) if response_times else 0
        }

    def _generate_recommendations(self, stats: Dict, documents: List, conversations: List) -> List[str]:
        """Génère des recommandations basées sur les statistiques."""
        recommendations = []
        
        if stats["avg_confidence_score"] < 0.6:
            recommendations.append("Considérez améliorer la qualité des documents source ou ajuster les paramètres de chunking.")
        
        if stats["avg_response_time"] > 5.0:
            recommendations.append("Les temps de réponse sont élevés. Considérez optimiser les modèles ou la taille des chunks.")
        
        if len(documents) < 3:
            recommendations.append("Ajoutez plus de documents pour améliorer la richesse des réponses.")
        
        if not conversations:
            recommendations.append("Commencez à poser des questions pour générer des insights.")
        
        # Recommandations basées sur l'utilisation des modèles
        if stats["model_usage"]:
            most_used_model = max(stats["model_usage"], key=stats["model_usage"].get)
            if "gpt-4" not in most_used_model and stats["avg_confidence_score"] < 0.7:
                recommendations.append("Considérez utiliser un modèle plus avancé comme GPT-4 pour améliorer la qualité.")
        
        return recommendations

    def _generate_system_recommendations(self, conversations: List) -> List[str]:
        """Génère des recommandations pour le système global."""
        recommendations = []
        
        if len(conversations) == 0:
            recommendations.append("Le système n'a pas encore été utilisé. Encouragez l'adoption.")
            return recommendations
        
        # Analyser les patterns d'erreur
        error_patterns = {}
        for conv in conversations[-100:]:  # Dernières 100 conversations
            if conv.confidence_score and conv.confidence_score < 0.3:
                # Question problématique
                words = conv.question.lower().split()[:3]  # Premiers mots
                pattern = " ".join(words)
                error_patterns[pattern] = error_patterns.get(pattern, 0) + 1
        
        if error_patterns:
            most_common_error = max(error_patterns, key=error_patterns.get)
            recommendations.append(f"Pattern de questions problématiques détecté: '{most_common_error}'. Considérez améliorer la documentation ou les prompts.")
        
        # Analyser la performance
        recent_response_times = [c.response_time for c in conversations[-50:] if c.response_time]
        if recent_response_times and sum(recent_response_times) / len(recent_response_times) > 3.0:
            recommendations.append("Les temps de réponse récents sont élevés. Vérifiez les performances du système.")
        
        return recommendations

    def _generate_html_report(self, data: Dict, template_name: str) -> str:
        """Génère un rapport HTML."""
        template = Template(self.report_templates[template_name])
        return template.render(**data)

    def _generate_csv_report(self, data: Dict) -> str:
        """Génère un rapport CSV."""
        # Créer un CSV des conversations
        conversations = data.get("conversations_summary", {}).get("conversations_timeline", [])
        
        csv_content = "timestamp,question,response_time,confidence_score,sources_count,model_used\n"
        for conv in conversations:
            csv_content += f"{conv['timestamp']},{conv['question']},{conv['response_time']},{conv['confidence_score']},{conv['sources_count']},{conv['model_used']}\n"
        
        return csv_content

    def _export_to_csv(self, conversations: List, session_id: str) -> str:
        """Exporte les conversations en CSV."""
        filename = f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join("exports", filename)
        
        os.makedirs("exports", exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "timestamp", "question", "answer", "response_time", 
                "confidence_score", "sources_count", "model_used"
            ])
            
            for conv in conversations:
                writer.writerow([
                    conv.timestamp.isoformat(),
                    conv.question,
                    conv.answer,
                    conv.response_time,
                    conv.confidence_score,
                    conv.sources_count,
                    conv.model_used
                ])
        
        return filepath

    def _export_to_json(self, conversations: List, session_id: str) -> str:
        """Exporte les conversations en JSON."""
        filename = f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join("exports", filename)
        
        os.makedirs("exports", exist_ok=True)
        
        data = []
        for conv in conversations:
            data.append({
                "timestamp": conv.timestamp.isoformat(),
                "question": conv.question,
                "answer": conv.answer,
                "response_time": conv.response_time,
                "confidence_score": conv.confidence_score,
                "sources_count": conv.sources_count,
                "model_used": conv.model_used
            })
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        
        return filepath

    def _get_session_summary_template(self) -> str:
        """Template HTML pour le rapport de session."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rapport de Session - {{ session_info.name }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background: #2a5298; color: white; padding: 20px; border-radius: 8px; }
                .section { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }
                .metric { display: inline-block; margin: 10px; padding: 15px; background: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .recommendation { background: #fff3cd; padding: 10px; margin: 5px 0; border-left: 4px solid #ffc107; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Rapport de Session: {{ session_info.name }}</h1>
                <p>Généré le {{ generated_at }}</p>
            </div>
            
            <div class="section">
                <h2>Résumé des Documents</h2>
                <div class="metric">
                    <strong>{{ documents_summary.total_documents }}</strong><br>Documents
                </div>
                <div class="metric">
                    <strong>{{ documents_summary.total_chunks }}</strong><br>Chunks
                </div>
                <div class="metric">
                    <strong>{{ "%.1f"|format(documents_summary.avg_processing_time) }}s</strong><br>Temps moyen
                </div>
            </div>
            
            <div class="section">
                <h2>Performance des Conversations</h2>
                <div class="metric">
                    <strong>{{ conversations_summary.total_conversations }}</strong><br>Conversations
                </div>
                <div class="metric">
                    <strong>{{ "%.2f"|format(conversations_summary.avg_response_time) }}s</strong><br>Temps moyen
                </div>
                <div class="metric">
                    <strong>{{ "%.2f"|format(conversations_summary.avg_confidence_score) }}</strong><br>Confiance moyenne
                </div>
            </div>
            
            <div class="section">
                <h2>Recommandations</h2>
                {% for rec in recommendations %}
                <div class="recommendation">{{ rec }}</div>
                {% endfor %}
            </div>
        </body>
        </html>
        """

    def _get_performance_template(self) -> str:
        """Template pour le rapport de performance."""
        return "<!-- Template de performance à implémenter -->"

    def _get_evaluation_template(self) -> str:
        """Template pour le rapport d'évaluation."""
        return "<!-- Template d'évaluation à implémenter -->"

# Instance globale du générateur de rapports
report_generator = ReportGenerator()
