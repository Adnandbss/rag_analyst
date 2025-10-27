"""
Gestionnaire de cache pour optimiser les performances et réduire les coûts.
Utilise diskcache pour la persistance locale gratuite.
"""

from typing import Any, Optional, Callable
import hashlib
import json
from diskcache import Cache
import structlog
from functools import wraps
import time

logger = structlog.get_logger(__name__)

# Cache global
embedding_cache = Cache('./cache/embeddings', size_limit=2**30)  # 1GB
response_cache = Cache('./cache/responses', size_limit=2**30)    # 1GB

class CacheManager:
    """Gestionnaire de cache intelligent."""
    
    def __init__(self, cache_dir: str = './cache', ttl: int = 86400):
        """
        Initialise le gestionnaire de cache.
        
        Args:
            cache_dir: Dossier de cache
            ttl: Time to live en secondes (défaut: 24h)
        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        
        # Créer les caches spécialisés
        self.embedding_cache = Cache(f'{cache_dir}/embeddings', size_limit=2**30)
        self.response_cache = Cache(f'{cache_dir}/responses', size_limit=2**30)
        self.document_cache = Cache(f'{cache_dir}/documents', size_limit=5**30)  # 5GB
        
        logger.info("Cache manager initialized", cache_dir=cache_dir, ttl=ttl)

    def _generate_key(self, *args, **kwargs) -> str:
        """Génère une clé de cache unique."""
        # Combiner tous les arguments dans une chaîne
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        
        # Hasher pour créer une clé courte
        return hashlib.md5(key_data.encode()).hexdigest()

    def cache_embedding(self, text: str, model: str = "text-embedding-ada-002"):
        """
        Décorateur pour cacher les embeddings.
        
        Usage:
            @cache_manager.cache_embedding
            def get_embedding(text, model):
                return expensive_api_call(text, model)
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(text: str, model: str = model):
                # Générer la clé de cache
                cache_key = self._generate_key(text, model)
                
                # Chercher dans le cache
                cached = self.embedding_cache.get(cache_key)
                if cached is not None:
                    logger.debug("Embedding cache hit", key=cache_key[:8])
                    return cached
                
                # Calculer et cacher
                logger.debug("Embedding cache miss", key=cache_key[:8])
                result = func(text, model)
                self.embedding_cache.set(cache_key, result, expire=self.ttl)
                
                return result
            
            return wrapper
        return decorator

    def cache_response(self, question: str, session_id: str, ttl: Optional[int] = None):
        """
        Cache une réponse RAG.
        
        Note: Utiliser avec précaution - les documents peuvent changer
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(question: str, session_id: str, *args, **kwargs):
                cache_key = self._generate_key(question, session_id)
                
                cached = self.response_cache.get(cache_key)
                if cached is not None:
                    logger.info("Response cache hit", 
                               question=question[:30],
                               session_id=session_id)
                    return cached
                
                result = func(question, session_id, *args, **kwargs)
                
                cache_ttl = ttl if ttl is not None else self.ttl
                self.response_cache.set(cache_key, result, expire=cache_ttl)
                
                return result
            
            return wrapper
        return decorator

    def get_cache_stats(self) -> dict:
        """Retourne les statistiques du cache."""
        return {
            "embeddings": {
                "size": len(self.embedding_cache),
                "volume": self.embedding_cache.volume(),
                "hits": self.embedding_cache.stats().get('hits', 0),
                "misses": self.embedding_cache.stats().get('misses', 0)
            },
            "responses": {
                "size": len(self.response_cache),
                "volume": self.response_cache.volume(),
                "hits": self.response_cache.stats().get('hits', 0),
                "misses": self.response_cache.stats().get('misses', 0)
            },
            "documents": {
                "size": len(self.document_cache),
                "volume": self.document_cache.volume()
            }
        }

    def clear_cache(self, cache_type: str = "all"):
        """
        Vide le cache.
        
        Args:
            cache_type: "embeddings", "responses", "documents", ou "all"
        """
        if cache_type in ["embeddings", "all"]:
            self.embedding_cache.clear()
            logger.info("Embeddings cache cleared")
        
        if cache_type in ["responses", "all"]:
            self.response_cache.clear()
            logger.info("Responses cache cleared")
        
        if cache_type in ["documents", "all"]:
            self.document_cache.clear()
            logger.info("Documents cache cleared")

    def optimize_cache(self):
        """Optimise le cache en supprimant les entrées expirées."""
        self.embedding_cache.expire()
        self.response_cache.expire()
        self.document_cache.expire()
        
        logger.info("Cache optimized")


class BatchProcessor:
    """Processeur batch pour traiter plusieurs documents/requêtes efficacement."""
    
    def __init__(self, batch_size: int = 10):
        """
        Initialise le processeur batch.
        
        Args:
            batch_size: Taille des batchs
        """
        self.batch_size = batch_size
        logger.info("Batch processor initialized", batch_size=batch_size)

    def batch_embed_texts(self, texts: list, embedding_func: Callable) -> list:
        """
        Traite les embeddings par batch pour optimiser les appels API.
        
        Args:
            texts: Liste de textes à embedder
            embedding_func: Fonction d'embedding
            
        Returns:
            Liste d'embeddings
        """
        embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            logger.debug("Processing embedding batch",
                        batch_num=i//self.batch_size + 1,
                        batch_size=len(batch))
            
            # Traiter le batch
            batch_embeddings = [embedding_func(text) for text in batch]
            embeddings.extend(batch_embeddings)
        
        return embeddings

    def batch_process_documents(self, documents: list, process_func: Callable) -> list:
        """
        Traite plusieurs documents en parallèle (simulation).
        
        Args:
            documents: Liste de documents
            process_func: Fonction de traitement
            
        Returns:
            Résultats du traitement
        """
        results = []
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            
            # Traiter séquentiellement (en production, utiliser ThreadPoolExecutor)
            batch_results = [process_func(doc) for doc in batch]
            results.extend(batch_results)
        
        return results


class CompressionManager:
    """Gestionnaire de compression pour optimiser le stockage et le transfert."""
    
    @staticmethod
    def compress_response(response: dict) -> dict:
        """
        Compresse une réponse en supprimant les informations redondantes.
        
        Args:
            response: Réponse complète
            
        Returns:
            Réponse compressée
        """
        compressed = response.copy()
        
        # Réduire la taille des sources
        if "sources" in compressed and compressed["sources"]:
            compressed["sources"] = [
                {
                    "content": src["content"][:500] + "..." if len(src["content"]) > 500 else src["content"],
                    "metadata": {k: v for k, v in src.get("metadata", {}).items() if k in ["source_file", "page"]}
                }
                for src in compressed["sources"][:3]  # Limiter à 3 sources
            ]
        
        return compressed

    @staticmethod
    def compress_reasoning_steps(steps: list) -> list:
        """Compresse les étapes de raisonnement de l'agent."""
        return [
            {
                "tool": step["tool"],
                "input": step["tool_input"][:100] + "..." if len(str(step["tool_input"])) > 100 else step["tool_input"],
                "output": step["observation"][:200] + "..." if len(step["observation"]) > 200 else step["observation"]
            }
            for step in steps[:5]  # Limiter à 5 étapes
        ]


# Instances globales
cache_manager = CacheManager()
batch_processor = BatchProcessor(batch_size=10)
compression_manager = CompressionManager()

