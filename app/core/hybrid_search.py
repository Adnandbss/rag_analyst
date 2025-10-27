"""
Hybrid Search combinant recherche sémantique (embeddings) et recherche par mots-clés (BM25).
Cette approche améliore significativement la pertinence des résultats.
"""

from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
from langchain.schema import Document
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

class HybridRetriever:
    """
    Retriever hybride combinant BM25 (keyword search) et recherche vectorielle (semantic search).
    """
    
    def __init__(self, documents: List[Document], vector_store, k: int = 5, 
                 alpha: float = 0.5):
        """
        Initialise le retriever hybride.
        
        Args:
            documents: Liste de documents pour BM25
            vector_store: Vector store pour la recherche sémantique
            k: Nombre de documents à retourner
            alpha: Poids de la recherche sémantique (0-1). 
                   alpha=1 : 100% semantic, alpha=0 : 100% BM25
        """
        self.documents = documents
        self.vector_store = vector_store
        self.k = k
        self.alpha = alpha
        
        # Initialiser BM25
        tokenized_docs = [doc.page_content.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)
        
        logger.info("Hybrid retriever initialized", 
                   documents_count=len(documents),
                   k=k,
                   alpha=alpha)

    def retrieve(self, query: str) -> List[Document]:
        """
        Récupère les documents les plus pertinents en combinant BM25 et semantic search.
        
        Args:
            query: Question de l'utilisateur
            
        Returns:
            Liste des documents les plus pertinents
        """
        # 1. Recherche BM25 (keyword-based)
        bm25_scores = self._get_bm25_scores(query)
        
        # 2. Recherche sémantique (vector-based)
        semantic_scores = self._get_semantic_scores(query)
        
        # 3. Fusionner les scores avec RRF (Reciprocal Rank Fusion)
        combined_scores = self._reciprocal_rank_fusion(bm25_scores, semantic_scores)
        
        # 4. Sélectionner les top-k documents
        top_indices = np.argsort(combined_scores)[-self.k:][::-1]
        
        results = [self.documents[i] for i in top_indices]
        
        logger.info("Hybrid search completed",
                   query=query[:50],
                   results_count=len(results))
        
        return results

    def _get_bm25_scores(self, query: str) -> np.ndarray:
        """Calcule les scores BM25 pour tous les documents."""
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Normaliser les scores entre 0 et 1
        if scores.max() > 0:
            scores = scores / scores.max()
        
        return scores

    def _get_semantic_scores(self, query: str) -> np.ndarray:
        """Calcule les scores de similarité sémantique."""
        # Utiliser le vector store pour faire une recherche avec scores
        results_with_scores = self.vector_store.similarity_search_with_score(
            query, 
            k=len(self.documents)  # Récupérer tous les documents avec scores
        )
        
        # Créer un tableau de scores aligné avec self.documents
        scores = np.zeros(len(self.documents))
        
        for doc, score in results_with_scores:
            # Trouver l'index de ce document
            for i, orig_doc in enumerate(self.documents):
                if orig_doc.page_content == doc.page_content:
                    # ChromaDB retourne une distance, on la convertit en similarité
                    scores[i] = 1 / (1 + score)  # Plus la distance est petite, plus le score est élevé
                    break
        
        # Normaliser
        if scores.max() > 0:
            scores = scores / scores.max()
        
        return scores

    def _reciprocal_rank_fusion(self, bm25_scores: np.ndarray, 
                                semantic_scores: np.ndarray, 
                                k: int = 60) -> np.ndarray:
        """
        Fusionne les scores avec Reciprocal Rank Fusion.
        RRF(d) = sum(1 / (k + rank_i(d))) pour chaque ranking system i
        
        Args:
            bm25_scores: Scores BM25
            semantic_scores: Scores sémantiques
            k: Constante de RRF (généralement 60)
            
        Returns:
            Scores fusionnés
        """
        # Convertir les scores en rangs
        bm25_ranks = np.argsort(np.argsort(bm25_scores)[::-1])
        semantic_ranks = np.argsort(np.argsort(semantic_scores)[::-1])
        
        # Appliquer RRF
        rrf_scores = np.zeros(len(bm25_scores))
        
        for i in range(len(bm25_scores)):
            rrf_scores[i] = (
                self.alpha / (k + semantic_ranks[i]) +
                (1 - self.alpha) / (k + bm25_ranks[i])
            )
        
        return rrf_scores

    def _weighted_fusion(self, bm25_scores: np.ndarray, 
                        semantic_scores: np.ndarray) -> np.ndarray:
        """
        Fusion simple par moyenne pondérée.
        Alternative plus simple à RRF.
        """
        return self.alpha * semantic_scores + (1 - self.alpha) * bm25_scores


class CrossEncoderReranker:
    """
    Reranker utilisant un CrossEncoder pour affiner les résultats.
    Le CrossEncoder évalue directement la pertinence query-document.
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialise le reranker.
        
        Args:
            model_name: Nom du modèle CrossEncoder de Sentence-Transformers
        """
        from sentence_transformers import CrossEncoder
        
        self.model = CrossEncoder(model_name)
        self.model_name = model_name
        
        logger.info("CrossEncoder reranker initialized", model=model_name)

    def rerank(self, query: str, documents: List[Document], top_k: int = None) -> List[Document]:
        """
        Rerank les documents selon leur pertinence avec la query.
        
        Args:
            query: Question de l'utilisateur
            documents: Documents à reranker
            top_k: Nombre de documents à retourner (None = tous)
            
        Returns:
            Documents rerankés par pertinence décroissante
        """
        if not documents:
            return []
        
        # Préparer les paires (query, document)
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Calculer les scores de pertinence
        scores = self.model.predict(pairs)
        
        # Trier les documents par score décroissant
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Retourner les top-k
        reranked = [doc for doc, score in scored_docs[:top_k]] if top_k else [doc for doc, score in scored_docs]
        
        logger.info("Reranking completed",
                   query=query[:50],
                   input_docs=len(documents),
                   output_docs=len(reranked))
        
        return reranked


class HybridRAGPipeline:
    """
    Pipeline RAG amélioré avec Hybrid Search et Reranking.
    """
    
    def __init__(self, vector_store, documents: List[Document], 
                 use_reranking: bool = True, alpha: float = 0.5):
        """
        Initialise le pipeline hybride.
        
        Args:
            vector_store: Store vectoriel ChromaDB
            documents: Liste des documents
            use_reranking: Activer le reranking avec CrossEncoder
            alpha: Poids semantic vs BM25
        """
        self.vector_store = vector_store
        self.documents = documents
        self.use_reranking = use_reranking
        
        # Créer le retriever hybride
        self.hybrid_retriever = HybridRetriever(
            documents=documents,
            vector_store=vector_store,
            k=10,  # Récupérer plus de documents pour le reranking
            alpha=alpha
        )
        
        # Créer le reranker si activé
        self.reranker = CrossEncoderReranker() if use_reranking else None
        
        logger.info("Hybrid RAG Pipeline initialized",
                   documents_count=len(documents),
                   use_reranking=use_reranking,
                   alpha=alpha)

    def retrieve_and_rank(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Récupère et rerank les documents les plus pertinents.
        
        Args:
            query: Question de l'utilisateur
            top_k: Nombre final de documents à retourner
            
        Returns:
            Documents finaux après hybrid search et reranking
        """
        # 1. Hybrid search
        hybrid_results = self.hybrid_retriever.retrieve(query)
        
        # 2. Reranking (optionnel)
        if self.use_reranking and self.reranker:
            final_results = self.reranker.rerank(query, hybrid_results, top_k=top_k)
        else:
            final_results = hybrid_results[:top_k]
        
        return final_results

    def compare_search_methods(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Compare les résultats de différentes méthodes de recherche.
        Utile pour benchmarking et A/B testing.
        
        Returns:
            Dictionnaire avec les résultats de chaque méthode
        """
        # 1. Recherche sémantique pure
        semantic_results = self.vector_store.similarity_search(query, k=top_k)
        
        # 2. Recherche BM25 pure
        tokenized_query = query.lower().split()
        bm25_scores = self.hybrid_retriever.bm25.get_scores(tokenized_query)
        top_bm25_indices = np.argsort(bm25_scores)[-top_k:][::-1]
        bm25_results = [self.documents[i] for i in top_bm25_indices]
        
        # 3. Hybrid search
        hybrid_results = self.retrieve_and_rank(query, top_k)
        
        return {
            "query": query,
            "methods": {
                "semantic_only": {
                    "results": [doc.page_content[:100] + "..." for doc in semantic_results],
                    "count": len(semantic_results)
                },
                "bm25_only": {
                    "results": [doc.page_content[:100] + "..." for doc in bm25_results],
                    "count": len(bm25_results)
                },
                "hybrid_with_reranking": {
                    "results": [doc.page_content[:100] + "..." for doc in hybrid_results],
                    "count": len(hybrid_results)
                }
            }
        }

