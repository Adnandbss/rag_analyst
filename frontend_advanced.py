"""
Interface utilisateur avancée pour RAG Analyst avec gestion multi-sessions,
métriques en temps réel, et fonctionnalités professionnelles.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Any, Optional
import os

# Désactiver le proxy pour les connexions locales
os.environ['NO_PROXY'] = '127.0.0.1,localhost'

# Configuration de la page
st.set_page_config(
    page_title="RAG Analyst Professional",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration de l'API
API_BASE_URL = "http://127.0.0.1:8000"

# CSS personnalisé pour améliorer l'apparence
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2a5298;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    
    .session-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        margin: 0.5rem 0;
    }
    
    .evaluation-score {
        font-size: 1.2em;
        font-weight: bold;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
        margin: 0.25rem;
    }
    
    .score-excellent { background-color: #d4edda; color: #155724; }
    .score-good { background-color: #d1ecf1; color: #0c5460; }
    .score-average { background-color: #fff3cd; color: #856404; }
    .score-poor { background-color: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)

class RAGAnalystApp:
    """Application principale RAG Analyst Professional."""
    
    def __init__(self):
        self.api_url = API_BASE_URL
        self.current_session_id = None
        
        # Initialiser les états de session
        if "sessions" not in st.session_state:
            st.session_state.sessions = []
        if "current_session" not in st.session_state:
            st.session_state.current_session = None
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "system_metrics" not in st.session_state:
            st.session_state.system_metrics = {}

    def check_api_status(self) -> bool:
        """Vérifier le statut de l'API."""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Erreur de connexion API: {e}")
            return False

    def get_sessions(self) -> List[Dict]:
        """Récupérer toutes les sessions."""
        try:
            response = requests.get(f"{self.api_url}/sessions")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Erreur lors de la récupération des sessions: {e}")
        return []

    def create_session(self, name: str, description: str = "") -> Optional[Dict]:
        """Créer une nouvelle session."""
        try:
            data = {"name": name, "description": description}
            response = requests.post(f"{self.api_url}/sessions/create", json=data)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Erreur lors de la création: {response.text}")
        except Exception as e:
            st.error(f"Erreur de connexion: {e}")
        return None

    def upload_document(self, session_id: str, file) -> Optional[Dict]:
        """Uploader un document vers une session."""
        try:
            files = {"file": (file.name, file.getvalue(), file.type)}
            response = requests.post(
                f"{self.api_url}/sessions/{session_id}/upload", 
                files=files,
                timeout=300
            )
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Erreur lors de l'upload: {response.text}")
        except Exception as e:
            st.error(f"Erreur lors de l'upload: {e}")
        return None

    def ask_question(self, question: str, session_id: str = None, 
                    enable_evaluation: bool = False,
                    model_preference: str = "balanced",
                    use_agent: bool = False) -> Optional[Dict]:
        """Poser une question."""
        try:
            data = {
                "question": question,
                "session_id": session_id,
                "enable_evaluation": enable_evaluation,
                "model_preference": model_preference,
                "use_agent": use_agent
            }
            response = requests.post(f"{self.api_url}/ask", json=data, timeout=60)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Erreur lors de la question: {response.text}")
        except Exception as e:
            st.error(f"Erreur de connexion: {e}")
        return None

    def get_system_metrics(self) -> Dict:
        """Récupérer les métriques du système."""
        try:
            response = requests.get(f"{self.api_url}/metrics")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Erreur lors de la récupération des métriques: {e}")
        return {}

    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Récupérer le résumé d'une session."""
        try:
            response = requests.get(f"{self.api_url}/sessions/{session_id}/summary")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Erreur lors de la récupération du résumé: {e}")
        return None

    def render_header(self):
        """Afficher l'en-tête de l'application."""
        st.markdown("""
        <div class="main-header">
            <h1>🧠 RAG Analyst Professional</h1>
            <p>Plateforme d'analyse intelligente de documents avec IA générative avancée</p>
        </div>
        """, unsafe_allow_html=True)

    def render_sidebar(self):
        """Afficher la barre latérale avec les contrôles."""
        with st.sidebar:
            st.header("🔧 Configuration")
            
            # Vérification de l'API
            api_status = self.check_api_status()
            if api_status:
                st.success("✅ API Backend connectée")
            else:
                st.error("❌ API Backend non disponible")
                st.info("Lancez l'API avec: `uvicorn app.main:app --reload`")
                return False
            
            st.markdown("---")
            
            # Gestion des sessions
            st.subheader("📊 Gestion des Sessions")
            
            # Bouton pour actualiser les sessions
            if st.button("🔄 Actualiser les sessions"):
                st.session_state.sessions = self.get_sessions()
            
            # Créer une nouvelle session
            with st.expander("➕ Créer une nouvelle session"):
                new_session_name = st.text_input("Nom de la session")
                new_session_desc = st.text_area("Description (optionnelle)")
                
                if st.button("Créer"):
                    if new_session_name:
                        result = self.create_session(new_session_name, new_session_desc)
                        if result:
                            st.success(f"Session '{new_session_name}' créée!")
                            st.session_state.sessions = self.get_sessions()
                            st.rerun()
            
            # Sélection de session
            if not st.session_state.sessions:
                st.session_state.sessions = self.get_sessions()
            
            if st.session_state.sessions:
                session_options = {
                    f"{s['name']} ({s['documents_count']} docs)": s['session_id'] 
                    for s in st.session_state.sessions
                }
                
                selected_session = st.selectbox(
                    "Sélectionner une session",
                    options=list(session_options.keys()),
                    index=0 if session_options else None
                )
                
                if selected_session:
                    st.session_state.current_session = session_options[selected_session]
                    
                    # Afficher les détails de la session
                    session_data = next(
                        s for s in st.session_state.sessions 
                        if s['session_id'] == st.session_state.current_session
                    )
                    
                    st.markdown(f"""
                    <div class="session-card">
                        <h4>{session_data['name']}</h4>
                        <p><strong>Documents:</strong> {session_data['documents_count']}</p>
                        <p><strong>Conversations:</strong> {session_data['conversations_count']}</p>
                        <p><strong>Créée:</strong> {session_data['created_at'][:10]}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucune session disponible. Créez-en une nouvelle.")
            
            st.markdown("---")
            
            # Configuration des paramètres
            st.subheader("⚙️ Paramètres")
            
            # Préférence de modèle
            model_preference = st.selectbox(
                "Priorité du modèle",
                options=["balanced", "speed", "quality", "cost"],
                help="balanced: équilibre performance/coût, speed: réponses rapides, quality: meilleure qualité, cost: économique"
            )
            
            # Mode Agent IA (NOUVEAU)
            use_agent = st.checkbox(
                "🤖 Mode Agent IA",
                help="Active l'agent autonome avec outils (calculator, web search, etc.) - Plus puissant mais plus lent"
            )
            
            # Afficher les outils disponibles si agent activé
            if use_agent:
                with st.expander("🛠️ Outils disponibles"):
                    st.markdown("""
                    - 🧮 **Calculator** : Calculs mathématiques
                    - 🌐 **Web Search** : Recherche internet
                    - 📅 **DateTime** : Date/heure actuelle
                    - 📄 **Document Query** : Interroger les docs
                    - 📝 **Text Analysis** : Analyse de texte
                    """)
            
            # Évaluation automatique
            enable_evaluation = st.checkbox(
                "📊 Évaluation automatique",
                help="Active l'évaluation de la qualité des réponses (plus lent)"
            )
            
            # Sauvegarder les paramètres dans session_state
            st.session_state.model_preference = model_preference
            st.session_state.enable_evaluation = enable_evaluation
            st.session_state.use_agent = use_agent
            
            return True

    def render_metrics_dashboard(self):
        """Afficher le tableau de bord des métriques."""
        st.subheader("📈 Métriques du Système")
        
        metrics = self.get_system_metrics()
        if not metrics:
            st.warning("Aucune métrique disponible")
            return
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Questions Totales",
                value=metrics.get("total_questions", 0)
            )
        
        with col2:
            st.metric(
                label="Temps Moyen (s)",
                value=f"{metrics.get('avg_response_time', 0):.2f}"
            )
        
        with col3:
            st.metric(
                label="Score Confiance",
                value=f"{metrics.get('avg_confidence_score', 0):.2f}"
            )
        
        with col4:
            error_rate = metrics.get('error_rate', 0) * 100
            st.metric(
                label="Taux d'Erreur (%)",
                value=f"{error_rate:.1f}"
            )
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            # Graphique des scores
            scores_data = {
                'Métrique': ['Confiance', 'Évaluation'],
                'Score': [
                    metrics.get('avg_confidence_score', 0),
                    metrics.get('avg_evaluation_score', 0)
                ]
            }
            
            fig = px.bar(
                scores_data, 
                x='Métrique', 
                y='Score',
                title="Scores Moyens de Performance",
                color='Score',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Graphique circulaire de répartition
            usage_data = {
                'Catégorie': ['Documents', 'Chunks', 'Questions'],
                'Valeur': [
                    metrics.get('total_documents', 0),
                    metrics.get('total_chunks', 0),
                    metrics.get('total_questions', 0)
                ]
            }
            
            fig = px.pie(
                usage_data,
                values='Valeur',
                names='Catégorie',
                title="Répartition de l'Utilisation"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    def render_document_upload(self):
        """Afficher la section d'upload de documents."""
        st.subheader("📤 Gestion des Documents")
        
        if not st.session_state.current_session:
            st.warning("Veuillez sélectionner une session dans la barre latérale.")
            return
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_files = st.file_uploader(
                "Choisissez des fichiers PDF",
                type=['pdf'],
                accept_multiple_files=True,
                help="Vous pouvez uploader plusieurs PDFs simultanément"
            )
            
            if uploaded_files:
                if st.button("🚀 Traiter les Documents", type="primary"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    results = []
                    for i, file in enumerate(uploaded_files):
                        status_text.text(f"Traitement de {file.name}...")
                        progress_bar.progress((i + 1) / len(uploaded_files))
                        
                        with st.spinner(f"Traitement de {file.name}..."):
                            result = self.upload_document(st.session_state.current_session, file)
                            if result:
                                results.append(result)
                    
                    status_text.text("Traitement terminé!")
                    
                    # Afficher les résultats
                    if results:
                        st.success(f"✅ {len(results)} document(s) traité(s) avec succès!")
                        
                        # Tableau des résultats
                        df = pd.DataFrame([
                            {
                                "Fichier": r["filename"],
                                "Taille (KB)": f"{r['file_size'] / 1024:.1f}",
                                "Pages": r["pages_count"],
                                "Chunks": r["chunks_count"],
                                "Temps (s)": f"{r['processing_time']:.2f}"
                            }
                            for r in results
                        ])
                        
                        st.dataframe(df, use_container_width=True)
        
        with col2:
            # Résumé de la session courante
            if st.session_state.current_session:
                summary = self.get_session_summary(st.session_state.current_session)
                if summary:
                    st.markdown("### 📊 Résumé de Session")
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>{summary['session_name']}</h4>
                        <p><strong>Documents:</strong> {summary['documents_count']}</p>
                        <p><strong>Conversations:</strong> {summary['conversations_count']}</p>
                        <p><strong>Chunks totaux:</strong> {summary['total_chunks']}</p>
                        <p><strong>Temps moyen:</strong> {summary['avg_response_time']:.2f}s</p>
                    </div>
                    """, unsafe_allow_html=True)

    def get_score_class(self, score: float) -> str:
        """Retourne la classe CSS selon le score."""
        if score >= 0.8:
            return "score-excellent"
        elif score >= 0.6:
            return "score-good"
        elif score >= 0.4:
            return "score-average"
        else:
            return "score-poor"

    def render_chat_interface(self):
        """Afficher l'interface de chat avancée."""
        st.subheader("💬 Assistant IA Conversationnel")
        
        if not st.session_state.current_session:
            st.warning("Veuillez sélectionner une session avec des documents.")
            return
        
        # Affichage de l'historique des messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Afficher les métadonnées pour les réponses de l'assistant
                if message["role"] == "assistant" and "metadata" in message:
                    metadata = message["metadata"]
                    
                    # Scores d'évaluation
                    if "evaluation_result" in metadata and metadata["evaluation_result"]:
                        eval_result = metadata["evaluation_result"]
                        
                        st.markdown("#### 📊 Scores d'Évaluation")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            score = eval_result["overall_score"]
                            score_class = self.get_score_class(score)
                            st.markdown(f"""
                            <div class="evaluation-score {score_class}">
                                Score Global<br>{score:.2f}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            score = eval_result["relevance_score"]
                            score_class = self.get_score_class(score)
                            st.markdown(f"""
                            <div class="evaluation-score {score_class}">
                                Pertinence<br>{score:.2f}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            score = eval_result["faithfulness_score"]
                            score_class = self.get_score_class(score)
                            st.markdown(f"""
                            <div class="evaluation-score {score_class}">
                                Fidélité<br>{score:.2f}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Afficher le raisonnement de l'agent si disponible
                    if metadata.get("agent_used") and metadata.get("reasoning_steps"):
                        st.markdown("#### 🤖 Raisonnement de l'Agent")
                        
                        with st.expander(f"🧠 Étapes de réflexion ({len(metadata['reasoning_steps'])})"):
                            for i, step in enumerate(metadata["reasoning_steps"], 1):
                                st.markdown(f"**Étape {i}:**")
                                st.code(f"Outil: {step['tool']}\nEntrée: {step['tool_input']}", language="text")
                                st.info(f"Résultat: {step['observation'][:200]}...")
                        
                        # Afficher les outils utilisés
                        if metadata.get("tools_used"):
                            tools_str = ", ".join(metadata["tools_used"])
                            st.success(f"🛠️ Outils utilisés : {tools_str}")
                    
                    # Informations techniques
                    agent_indicator = "🤖 Agent IA" if metadata.get("agent_used") else "📄 RAG"
                    tech_info = f"{agent_indicator} | ⏱️ {metadata['response_time']:.2f}s | 🎯 {metadata['confidence_score']:.2f} | {metadata['model_used']}"
                    st.caption(tech_info)
                    
                    # Sources
                    if "sources" in metadata and metadata["sources"]:
                        with st.expander(f"📚 Sources ({len(metadata['sources'])})"):
                            for i, source in enumerate(metadata["sources"]):
                                st.markdown(f"**Source {i+1}:**")
                                st.text(source["content"][:300] + "..." if len(source["content"]) > 300 else source["content"])
                                if "metadata" in source:
                                    st.caption(f"📄 {source['metadata'].get('source_file', 'Document')}")
        
        # Interface de saisie
        if prompt := st.chat_input("Posez votre question sur les documents..."):
            # Ajouter le message de l'utilisateur
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Générer et afficher la réponse
            with st.chat_message("assistant"):
                loading_msg = "🤖 Agent IA en action..." if st.session_state.get("use_agent", False) else "🤔 Analyse en cours..."
                with st.spinner(loading_msg):
                    result = self.ask_question(
                        prompt,
                        st.session_state.current_session,
                        st.session_state.get("enable_evaluation", False),
                        st.session_state.get("model_preference", "balanced"),
                        st.session_state.get("use_agent", False)
                    )
                
                if result:
                    st.markdown(result["answer"])
                    
                    # Sauvegarder la réponse avec métadonnées
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "metadata": {
                            "response_time": result["response_time"],
                            "confidence_score": result["confidence_score"],
                            "model_used": result["model_used"],
                            "sources": result.get("sources", []),
                            "evaluation_result": result.get("evaluation_result"),
                            "agent_used": result.get("agent_used", False),
                            "reasoning_steps": result.get("reasoning_steps", []),
                            "tools_used": result.get("tools_used", [])
                        }
                    })
                    
                    st.rerun()
                else:
                    st.error("Impossible de traiter la question. Vérifiez la connexion à l'API.")

    def render_examples_section(self):
        """Afficher la section d'exemples de questions."""
        st.subheader("💡 Exemples de Questions")
        
        example_categories = {
            "📊 Analyse Financière": [
                "Quel est le chiffre d'affaires de l'entreprise pour l'année dernière ?",
                "Quelle est la marge bénéficiaire nette ?",
                "Comment évoluent les revenus par rapport à l'année précédente ?"
            ],
            "⚠️ Analyse des Risques": [
                "Quels sont les principaux risques mentionnés dans le document ?",
                "Y a-t-il des risques liés à la cybersécurité ?",
                "Comment l'entreprise gère-t-elle les risques réglementaires ?"
            ],
            "🚀 Stratégie & Développement": [
                "Quelles sont les perspectives d'avenir de l'entreprise ?",
                "Y a-t-il des acquisitions ou partenariats prévus ?",
                "Quels sont les investissements en R&D ?"
            ]
        }
        
        cols = st.columns(3)
        
        for i, (category, questions) in enumerate(example_categories.items()):
            with cols[i % 3]:
                st.markdown(f"**{category}**")
                for question in questions:
                    if st.button(question, key=f"example_{hash(question)}", use_container_width=True):
                        # Ajouter la question aux messages et traiter
                        st.session_state.example_question = question
                        st.rerun()

    def run(self):
        """Lancer l'application principale."""
        self.render_header()
        
        # Vérifier la connexion API dans la sidebar
        api_available = self.render_sidebar()
        
        if not api_available:
            return
        
        # Traiter une question d'exemple si sélectionnée
        if hasattr(st.session_state, 'example_question'):
            if st.session_state.current_session:
                # Simuler la saisie de la question d'exemple
                st.session_state.messages.append({
                    "role": "user", 
                    "content": st.session_state.example_question
                })
                
                # Traiter la question
                loading_msg = "🤖 Agent IA en action..." if st.session_state.get("use_agent", False) else "🤔 Analyse en cours..."
                with st.spinner(loading_msg):
                    result = self.ask_question(
                        st.session_state.example_question,
                        st.session_state.current_session,
                        st.session_state.get("enable_evaluation", False),
                        st.session_state.get("model_preference", "balanced"),
                        st.session_state.get("use_agent", False)
                    )
                
                if result:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "metadata": {
                            "response_time": result["response_time"],
                            "confidence_score": result["confidence_score"],
                            "model_used": result["model_used"],
                            "sources": result.get("sources", []),
                            "evaluation_result": result.get("evaluation_result"),
                            "agent_used": result.get("agent_used", False),
                            "reasoning_steps": result.get("reasoning_steps", []),
                            "tools_used": result.get("tools_used", [])
                        }
                    })
            
            # Nettoyer la question d'exemple
            del st.session_state.example_question
            st.rerun()
        
        # Interface principale avec onglets
        tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📤 Documents", "📈 Métriques", "💡 Exemples"])
        
        with tab1:
            self.render_chat_interface()
        
        with tab2:
            self.render_document_upload()
        
        with tab3:
            self.render_metrics_dashboard()
        
        with tab4:
            self.render_examples_section()

if __name__ == "__main__":
    app = RAGAnalystApp()
    app.run()
