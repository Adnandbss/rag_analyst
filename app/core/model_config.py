"""
Configuration multi-modèles pour différents LLMs et embeddings.
"""

from typing import Dict, Any, Optional
from enum import Enum
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
import structlog

logger = structlog.get_logger(__name__)

class ModelProvider(Enum):
    """Fournisseurs de modèles supportés."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"

class EmbeddingProvider(Enum):
    """Fournisseurs d'embeddings supportés."""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    SENTENCE_TRANSFORMERS = "sentence_transformers"

class ModelConfiguration:
    """Configuration centralisée pour tous les modèles."""
    
    def __init__(self):
        self.llm_configs = {
            ModelProvider.OPENAI: {
                "gpt-3.5-turbo": {
                    "model_name": "gpt-3.5-turbo",
                    "temperature": 0,
                    "max_tokens": 1000,
                    "cost_per_1k_tokens": 0.002
                },
                "gpt-4": {
                    "model_name": "gpt-4",
                    "temperature": 0,
                    "max_tokens": 1000,
                    "cost_per_1k_tokens": 0.03
                },
                "gpt-4-turbo": {
                    "model_name": "gpt-4-turbo-preview",
                    "temperature": 0,
                    "max_tokens": 1000,
                    "cost_per_1k_tokens": 0.01
                }
            },
            ModelProvider.OLLAMA: {
                "llama2": {
                    "model": "llama2",
                    "temperature": 0,
                    "cost_per_1k_tokens": 0  # Local model
                },
                "mistral": {
                    "model": "mistral",
                    "temperature": 0,
                    "cost_per_1k_tokens": 0
                },
                "codellama": {
                    "model": "codellama",
                    "temperature": 0,
                    "cost_per_1k_tokens": 0
                }
            }
        }
        
        self.embedding_configs = {
            EmbeddingProvider.OPENAI: {
                "text-embedding-ada-002": {
                    "model": "text-embedding-ada-002",
                    "dimensions": 1536,
                    "cost_per_1k_tokens": 0.0001
                },
                "text-embedding-3-small": {
                    "model": "text-embedding-3-small",
                    "dimensions": 1536,
                    "cost_per_1k_tokens": 0.00002
                },
                "text-embedding-3-large": {
                    "model": "text-embedding-3-large",
                    "dimensions": 3072,
                    "cost_per_1k_tokens": 0.00013
                }
            },
            EmbeddingProvider.HUGGINGFACE: {
                "all-MiniLM-L6-v2": {
                    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                    "dimensions": 384,
                    "cost_per_1k_tokens": 0  # Free
                },
                "all-mpnet-base-v2": {
                    "model_name": "sentence-transformers/all-mpnet-base-v2",
                    "dimensions": 768,
                    "cost_per_1k_tokens": 0
                }
            }
        }

    def get_llm(self, provider: ModelProvider, model_name: str, **kwargs):
        """Crée une instance de LLM selon la configuration."""
        try:
            if provider == ModelProvider.OPENAI:
                config = self.llm_configs[provider][model_name]
                # Merger les kwargs avec la config par défaut
                final_config = {**config, **kwargs}
                final_config.pop('cost_per_1k_tokens', None)  # Remove cost info
                
                return ChatOpenAI(**final_config)
            
            elif provider == ModelProvider.OLLAMA:
                config = self.llm_configs[provider][model_name]
                final_config = {**config, **kwargs}
                final_config.pop('cost_per_1k_tokens', None)
                
                return Ollama(**final_config)
            
            else:
                raise ValueError(f"Provider {provider} not yet implemented")
                
        except Exception as e:
            logger.error("Failed to create LLM", provider=provider.value, model=model_name, error=str(e))
            # Fallback vers OpenAI GPT-3.5
            return ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

    def get_embeddings(self, provider: EmbeddingProvider, model_name: str, **kwargs):
        """Crée une instance d'embeddings selon la configuration."""
        try:
            if provider == EmbeddingProvider.OPENAI:
                config = self.embedding_configs[provider][model_name]
                final_config = {**config, **kwargs}
                final_config.pop('cost_per_1k_tokens', None)
                final_config.pop('dimensions', None)  # OpenAI doesn't need this param
                
                return OpenAIEmbeddings(**final_config)
            
            elif provider == EmbeddingProvider.HUGGINGFACE:
                config = self.embedding_configs[provider][model_name]
                final_config = {**config, **kwargs}
                final_config.pop('cost_per_1k_tokens', None)
                final_config.pop('dimensions', None)
                
                return HuggingFaceEmbeddings(**final_config)
            
            else:
                raise ValueError(f"Embedding provider {provider} not yet implemented")
                
        except Exception as e:
            logger.error("Failed to create embeddings", provider=provider.value, model=model_name, error=str(e))
            # Fallback vers OpenAI
            return OpenAIEmbeddings()

    def get_available_models(self) -> Dict[str, Any]:
        """Retourne la liste des modèles disponibles."""
        return {
            "llm_models": {
                provider.value: list(configs.keys()) 
                for provider, configs in self.llm_configs.items()
            },
            "embedding_models": {
                provider.value: list(configs.keys())
                for provider, configs in self.embedding_configs.items()
            }
        }

    def get_model_cost(self, provider: ModelProvider, model_name: str) -> float:
        """Retourne le coût par 1k tokens du modèle."""
        try:
            return self.llm_configs[provider][model_name]["cost_per_1k_tokens"]
        except KeyError:
            return 0.0

    def get_embedding_cost(self, provider: EmbeddingProvider, model_name: str) -> float:
        """Retourne le coût par 1k tokens de l'embedding."""
        try:
            return self.embedding_configs[provider][model_name]["cost_per_1k_tokens"]
        except KeyError:
            return 0.0

class AdaptiveModelSelector:
    """Sélectionneur adaptatif de modèles selon le contexte."""
    
    def __init__(self, config: ModelConfiguration):
        self.config = config
        self.usage_stats = {}

    def select_best_model(self, 
                         task_type: str = "general",
                         budget_constraint: Optional[float] = None,
                         performance_priority: str = "balanced") -> tuple:
        """
        Sélectionne le meilleur modèle selon les critères donnés.
        
        Args:
            task_type: Type de tâche ("general", "analysis", "summarization", etc.)
            budget_constraint: Budget maximum par requête
            performance_priority: "speed", "quality", "balanced", "cost"
        
        Returns:
            tuple: (provider, model_name, reasoning)
        """
        
        if performance_priority == "cost" or budget_constraint and budget_constraint < 0.001:
            # Privilégier les modèles gratuits/peu chers
            return ModelProvider.OLLAMA, "mistral", "Cost optimization"
        
        elif performance_priority == "speed":
            # Privilégier les modèles rapides
            return ModelProvider.OPENAI, "gpt-3.5-turbo", "Speed optimization"
        
        elif performance_priority == "quality":
            # Privilégier la qualité
            if not budget_constraint or budget_constraint >= 0.01:
                return ModelProvider.OPENAI, "gpt-4", "Quality optimization"
            else:
                return ModelProvider.OPENAI, "gpt-3.5-turbo", "Quality with budget constraint"
        
        else:  # balanced
            return ModelProvider.OPENAI, "gpt-3.5-turbo", "Balanced choice"

    def select_best_embeddings(self, 
                              performance_priority: str = "balanced",
                              budget_constraint: Optional[float] = None) -> tuple:
        """Sélectionne les meilleurs embeddings."""
        
        if performance_priority == "cost" or budget_constraint and budget_constraint < 0.0001:
            return EmbeddingProvider.HUGGINGFACE, "all-MiniLM-L6-v2", "Cost optimization"
        
        elif performance_priority == "quality":
            return EmbeddingProvider.OPENAI, "text-embedding-3-large", "Quality optimization"
        
        else:  # balanced or speed
            return EmbeddingProvider.OPENAI, "text-embedding-ada-002", "Balanced choice"

# Instance globale de configuration
model_config = ModelConfiguration()
adaptive_selector = AdaptiveModelSelector(model_config)
