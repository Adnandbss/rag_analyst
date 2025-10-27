import os
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from dotenv import load_dotenv

# Charger les variables d'environnement (notamment la clé API OpenAI)
load_dotenv()

# Constantes pour la configuration
CHROMA_DB_PATH = "./chroma_db"
PDF_STORAGE_PATH = "./pdf_storage"

def load_and_process_pdf(pdf_path: str) -> list:
    """
    Charge un fichier PDF, le divise en chunks et retourne les documents.
    """
    print(f"Chargement du document : {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = text_splitter.split_documents(documents)
    print(f"Document divisé en {len(split_docs)} chunks.")
    return split_docs

def create_or_get_vectorstore(documents: list = None, force_recreate: bool = False):
    """
    Crée une base de données vectorielle Chroma à partir des documents
    ou charge une base existante si elle est présente sur le disque.
    """
    embeddings = OpenAIEmbeddings()
    
    if os.path.exists(CHROMA_DB_PATH) and not force_recreate:
        print(f"Chargement de la base de données vectorielle depuis : {CHROMA_DB_PATH}")
        vectorstore = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=embeddings)
    elif documents:
        print("Création d'une nouvelle base de données vectorielle...")
        vectorstore = Chroma.from_documents(
            documents=documents, 
            embedding=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        print("Base de données vectorielle créée et sauvegardée.")
    else:
        raise ValueError("Aucun document fourni et aucune base de données existante à charger.")

    return vectorstore

def create_rag_chain(vectorstore):
    """
    Crée et retourne une chaîne de Retrieval-QA.
    """
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
        return_source_documents=True
    )
    print("Chaîne RAG créée.")
    return qa_chain

def ask_question(chain, question: str) -> dict:
    """
    Pose une question à la chaîne RAG et retourne la réponse.
    """
    print(f"\nQuestion: {question}")
    result = chain({"query": question})
    print(f"Réponse: {result['result']}")
    return result
