"""
Optimisation et reformulation de requêtes pour améliorer la qualité du retrieval.
Techniques: Query expansion, Multi-query, HyDE (Hypothetical Document Embeddings).
"""

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import structlog

logger = structlog.get_logger(__name__)

class QueryOptimizer:
    """Optimiseur de requêtes pour améliorer le retrieval."""
    
    def __init__(self, llm=None):
        """
        Initialise l'optimiseur de requêtes.
        
        Args:
            llm: Modèle de langage pour la génération de variations
        """
        self.llm = llm or ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
        
        # Prompts pour différentes stratégies
        self.expansion_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Génère 3 variations de cette question qui pourraient aider à trouver la même information dans un document.
Les variations doivent utiliser des synonymes, des formulations différentes, ou des angles d'approche complémentaires.

Question originale: {query}

Variations (une par ligne):
1."""
        )
        
        self.hyde_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Génère un passage hypothétique de document qui répondrait parfaitement à cette question.
Le passage doit être factuel et détaillé, comme s'il était extrait d'un document professionnel.

Question: {query}

Passage hypothétique:"""
        )
        
        self.decomposition_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Décompose cette question complexe en sous-questions plus simples et indépendantes.
Chaque sous-question doit pouvoir être répondue séparément.

Question complexe: {query}

Sous-questions (une par ligne):
1."""
        )
        
        logger.info("Query optimizer initialized")

    def expand_query(self, query: str) -> List[str]:
        """
        Query Expansion: Génère plusieurs variations de la question.
        
        Args:
            query: Question originale
            
        Returns:
            Liste de variations incluant la question originale
        """
        try:
            prompt = self.expansion_prompt.format(query=query)
            response = self.llm.invoke(prompt)
            
            # Parser les variations
            variations = [query]  # Inclure la question originale
            
            # Extraire les lignes numérotées
            lines = response.content.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Ignorer les lignes vides ou trop courtes
                    # Nettoyer les numéros
                    cleaned = line.lstrip('0123456789.-) ')
                    if cleaned and cleaned != query:
                        variations.append(cleaned)
            
            logger.info("Query expansion completed",
                       original=query[:50],
                       variations_count=len(variations))
            
            return variations[:4]  # Maximum 4 variations (original + 3)
            
        except Exception as e:
            logger.error("Query expansion failed", query=query[:50], error=str(e))
            return [query]

    def generate_hyde_document(self, query: str) -> str:
        """
        HyDE (Hypothetical Document Embeddings): Génère un document hypothétique.
        Ce document est utilisé pour la recherche sémantique au lieu de la query directe.
        
        Args:
            query: Question de l'utilisateur
            
        Returns:
            Document hypothétique
        """
        try:
            prompt = self.hyde_prompt.format(query=query)
            response = self.llm.invoke(prompt)
            
            hypothetical_doc = response.content.strip()
            
            logger.info("HyDE document generated",
                       query=query[:50],
                       doc_length=len(hypothetical_doc))
            
            return hypothetical_doc
            
        except Exception as e:
            logger.error("HyDE generation failed", query=query[:50], error=str(e))
            return query  # Fallback vers la query originale

    def decompose_query(self, query: str) -> List[str]:
        """
        Query Decomposition: Décompose une question complexe en sous-questions.
        
        Args:
            query: Question complexe
            
        Returns:
            Liste de sous-questions
        """
        try:
            prompt = self.decomposition_prompt.format(query=query)
            response = self.llm.invoke(prompt)
            
            # Parser les sous-questions
            sub_questions = []
            
            lines = response.content.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:
                    cleaned = line.lstrip('0123456789.-) ')
                    if cleaned:
                        sub_questions.append(cleaned)
            
            # Si aucune sous-question trouvée, retourner la question originale
            if not sub_questions:
                sub_questions = [query]
            
            logger.info("Query decomposition completed",
                       original=query[:50],
                       sub_questions_count=len(sub_questions))
            
            return sub_questions
            
        except Exception as e:
            logger.error("Query decomposition failed", query=query[:50], error=str(e))
            return [query]

    def optimize_query(self, query: str, strategy: str = "expansion") -> Any:
        """
        Optimise une query selon la stratégie choisie.
        
        Args:
            query: Question originale
            strategy: Stratégie d'optimisation ("expansion", "hyde", "decomposition")
            
        Returns:
            Résultat selon la stratégie (List[str] ou str)
        """
        if strategy == "expansion":
            return self.expand_query(query)
        elif strategy == "hyde":
            return self.generate_hyde_document(query)
        elif strategy == "decomposition":
            return self.decompose_query(query)
        else:
            logger.warning("Unknown optimization strategy", strategy=strategy)
            return [query]

    def extract_keywords(self, query: str) -> List[str]:
        """
        Extrait les mots-clés importants de la query.
        Utile pour le highlighting et le debugging.
        
        Args:
            query: Question
            
        Returns:
            Liste de mots-clés
        """
        # Simple extraction basée sur la longueur et la fréquence
        stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 
                     'est', 'sont', 'a', 'au', 'aux', 'dans', 'pour', 'par',
                     'sur', 'avec', 'quel', 'quelle', 'quels', 'quelles', 'comment',
                     'pourquoi', 'qui', 'que', 'quoi'}
        
        words = query.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return keywords[:5]  # Top 5 keywords


# Instance globale de l'optimiseur
query_optimizer = QueryOptimizer()

