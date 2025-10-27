import os
import argparse
from app.core.rag_pipeline import (
    load_and_process_pdf,
    create_or_get_vectorstore,
    create_rag_chain,
    ask_question,
    PDF_STORAGE_PATH
)

def main():
    """
    Point d'entrée principal pour l'interface en ligne de commande (CLI).
    Permet de traiter un PDF et de poser des questions à son sujet.
    """
    parser = argparse.ArgumentParser(description="RAG Analyst CLI - Interrogez vos documents PDF.")
    parser.add_argument("pdf_name", type=str, help="Le nom du fichier PDF à analyser (doit être dans le dossier pdf_storage).")
    parser.add_argument("--force-recreate", action="store_true", help="Force la recréation de la base de données vectorielle même si elle existe déjà.")
    
    args = parser.parse_args()

    # Créer le répertoire de stockage PDF s'il n'existe pas
    if not os.path.exists(PDF_STORAGE_PATH):
        os.makedirs(PDF_STORAGE_PATH)

    pdf_path = os.path.join(PDF_STORAGE_PATH, args.pdf_name)

    if not os.path.exists(pdf_path):
        print(f"Erreur : Le fichier '{args.pdf_name}' n'a pas été trouvé dans le dossier '{PDF_STORAGE_PATH}'.")
        print("Veuillez y placer votre fichier PDF et réessayer.")
        return

    # Phase 1: Ingestion et traitement du PDF
    documents = load_and_process_pdf(pdf_path)

    # Phase 2: Création ou chargement de la base de données vectorielle
    vectorstore = create_or_get_vectorstore(documents, force_recreate=args.force_recreate)

    # Phase 3: Création de la chaîne RAG
    qa_chain = create_rag_chain(vectorstore)

    # Phase 4: Boucle d'interaction avec l'utilisateur
    print("\nL'assistant est prêt. Posez vos questions. Tapez 'exit' ou 'quit' pour quitter.")
    while True:
        try:
            user_question = input("\nVotre question: ")
            if user_question.lower() in ["exit", "quit"]:
                print("Au revoir !")
                break
            
            ask_question(qa_chain, user_question)

        except KeyboardInterrupt:
            print("\nAu revoir !")
            break

if __name__ == "__main__":
    main()
