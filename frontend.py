import streamlit as st
import requests
import os
from io import BytesIO

# Configuration de l'API backend
API_BASE_URL = "http://127.0.0.1:8000"

# Configuration de la page Streamlit
st.set_page_config(
    page_title="RAG Analyst",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("📄 RAG Analyst")
    st.markdown("**Assistant d'Analyse de Rapports Financiers**")
    st.markdown("---")

    # Sidebar pour les informations et les contrôles
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Vérification de l'état de l'API
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=5)
            if response.status_code == 200:
                st.success("✅ API Backend connectée")
            else:
                st.error("❌ API Backend non disponible")
        except requests.exceptions.RequestException:
            st.error("❌ API Backend non disponible")
            st.markdown("**Instructions :**")
            st.markdown("1. Ouvrez un terminal dans le dossier `rag_analyst`")
            st.markdown("2. Activez l'environnement : `.\venv\Scripts\\activate`")
            st.markdown("3. Lancez l'API : `uvicorn app.main:app --reload`")
        
        st.markdown("---")
        st.markdown("**Comment utiliser :**")
        st.markdown("1. 📤 Uploadez un document PDF")
        st.markdown("2. ⏳ Attendez le traitement")
        st.markdown("3. ❓ Posez vos questions")

    # Interface principale divisée en deux colonnes
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📤 Étape 1 : Upload du Document")
        
        uploaded_file = st.file_uploader(
            "Choisissez un fichier PDF", 
            type=['pdf'],
            help="Sélectionnez un rapport financier, un document d'entreprise, ou tout autre PDF à analyser."
        )
        
        if uploaded_file is not None:
            st.success(f"📄 Fichier sélectionné : {uploaded_file.name}")
            
            if st.button("🚀 Traiter le Document", type="primary"):
                with st.spinner("⏳ Traitement du document en cours... Cela peut prendre quelques minutes."):
                    try:
                        # Envoyer le fichier à l'API
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                        response = requests.post(f"{API_BASE_URL}/upload", files=files, timeout=300)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ {result['message']}")
                            st.session_state.document_ready = True
                        else:
                            st.error(f"❌ Erreur lors du traitement : {response.text}")
                            
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Erreur de connexion : {e}")

    with col2:
        st.header("❓ Étape 2 : Posez vos Questions")
        
        # Zone de chat
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Affichage de l'historique des messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                # Afficher les sources s'il y en a
                if message["role"] == "assistant" and "sources" in message:
                    with st.expander("📚 Sources utilisées"):
                        for i, source in enumerate(message["sources"]):
                            st.markdown(f"**Source {i+1}:**")
                            st.text(source["content"][:300] + "..." if len(source["content"]) > 300 else source["content"])

        # Interface de saisie
        question = st.chat_input("Posez votre question sur le document...")
        
        if question:
            # Ajouter la question de l'utilisateur
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            # Obtenir et afficher la réponse
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                try:
                    with st.spinner("🤔 Réflexion en cours..."):
                        response = requests.post(
                            f"{API_BASE_URL}/ask",
                            json={"question": question},
                            timeout=60
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        answer = result["answer"]
                        sources = result.get("source_documents", [])
                        
                        message_placeholder.markdown(answer)
                        
                        # Stocker la réponse avec les sources
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": answer,
                            "sources": sources
                        })
                        
                        # Afficher les sources
                        if sources:
                            with st.expander("📚 Sources utilisées"):
                                for i, source in enumerate(sources):
                                    st.markdown(f"**Source {i+1}:**")
                                    st.text(source["content"][:300] + "..." if len(source["content"]) > 300 else source["content"])
                    
                    elif response.status_code == 400:
                        error_message = "⚠️ Aucun document n'a été traité. Veuillez d'abord uploader et traiter un PDF."
                        message_placeholder.error(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
                    
                    else:
                        error_message = f"❌ Erreur lors de la requête : {response.text}"
                        message_placeholder.error(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
                        
                except requests.exceptions.RequestException as e:
                    error_message = f"❌ Erreur de connexion : {e}"
                    message_placeholder.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})

    # Section d'exemples de questions
    st.markdown("---")
    st.header("💡 Exemples de Questions")
    
    example_questions = [
        "Quel est le chiffre d'affaires de l'entreprise pour l'année dernière ?",
        "Quels sont les principaux risques mentionnés dans le document ?",
        "Quelle est la situation financière de l'entreprise ?",
        "Y a-t-il des acquisitions ou des partenariats mentionnés ?",
        "Quelles sont les perspectives d'avenir de l'entreprise ?"
    ]
    
    cols = st.columns(len(example_questions))
    for i, question in enumerate(example_questions):
        with cols[i]:
            if st.button(question, key=f"example_{i}"):
                # Simuler la saisie de la question
                st.session_state.example_question = question
                st.rerun()

if __name__ == "__main__":
    main()
