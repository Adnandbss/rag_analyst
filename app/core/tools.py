"""
Définition des outils pour les agents IA autonomes.
"""

from typing import Optional
from datetime import datetime
import math
import re
import requests
import json
import structlog

logger = structlog.get_logger(__name__)

class CalculatorTool:
    """Outil de calcul mathématique avancé."""
    
    name = "calculator"
    description = """Outil de calcul mathématique pour effectuer des opérations arithmétiques et mathématiques.
    Supporte : +, -, *, /, **, sqrt, pow, sin, cos, tan, log, etc.
    Exemple d'entrée : "sqrt(25) + 10 * 2"
    """
    
    @staticmethod
    def run(expression: str) -> str:
        """Évalue une expression mathématique."""
        try:
            # Nettoyer l'expression
            expression = expression.strip()
            
            # Contexte sécurisé avec fonctions mathématiques
            safe_dict = {
                "sqrt": math.sqrt,
                "pow": math.pow,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
            }
            
            # Évaluation sécurisée
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            
            logger.info("Calculator tool executed", expression=expression, result=result)
            return f"Résultat : {result}"
            
        except Exception as e:
            logger.error("Calculator tool error", expression=expression, error=str(e))
            return f"Erreur de calcul : {str(e)}"


class WebSearchTool:
    """Outil de recherche web avec API externe pour informations en temps réel."""
    
    name = "web_search"
    description = """Outil de recherche web pour trouver des informations récentes sur internet.
    Utilise des APIs externes pour des données en temps réel.
    Exemple d'entrée : "prix du bitcoin aujourd'hui"
    """
    
    @staticmethod
    def run(query: str, max_results: int = 3) -> str:
        """Effectue une recherche web."""
        try:
            # Recherche spécialisée pour le Bitcoin
            if "bitcoin" in query.lower() or "btc" in query.lower():
                return WebSearchTool._get_bitcoin_price()
            
            # Recherche spécialisée pour les crypto-monnaies
            if any(crypto in query.lower() for crypto in ["ethereum", "eth", "crypto", "cryptocurrency"]):
                return WebSearchTool._get_crypto_info(query)
            
            # Recherche générale avec API externe
            return WebSearchTool._general_search(query, max_results)
                
        except Exception as e:
            logger.error("Web search error", query=query, error=str(e))
            # En cas d'erreur, donner une réponse utile sans connexion
            return f"""🔍 **Recherche web temporairement indisponible**

Pour votre question "{query}", voici des informations générales :

💡 **Suggestions** :
- Pour les prix crypto : "prix bitcoin" ou "prix ethereum"
- Pour les calculs : "calcule 25 * 3.14"
- Pour la date : "quelle est la date d'aujourd'hui ?"

⚠️ **Erreur technique** : {str(e)}

*Les outils de calcul, date et analyse de texte fonctionnent sans connexion internet.*"""
    
    @staticmethod
    def _get_bitcoin_price() -> str:
        """Récupère le prix du Bitcoin en temps réel."""
        try:
            # Utiliser l'API CoinGecko (gratuite, pas de clé requise)
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur&include_24hr_change=true",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                btc_data = data.get('bitcoin', {})
                
                price_usd = btc_data.get('usd', 'N/A')
                price_eur = btc_data.get('eur', 'N/A')
                change_24h = btc_data.get('usd_24h_change', 'N/A')
                
                change_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
                
                return f"""💰 **Prix du Bitcoin en temps réel** {change_emoji}

💵 **USD** : ${price_usd:,.2f}
💶 **EUR** : €{price_eur:,.2f}
📊 **Variation 24h** : {change_24h:+.2f}%

🕐 Mis à jour : {datetime.now().strftime('%H:%M:%S')}

*Source : CoinGecko API*"""
            
            else:
                return "Impossible de récupérer le prix du Bitcoin. Veuillez réessayer plus tard."
                
        except Exception as e:
            return f"Erreur lors de la récupération du prix Bitcoin : {str(e)}"
    
    @staticmethod
    def _get_crypto_info(query: str) -> str:
        """Récupère des informations sur les crypto-monnaies."""
        try:
            # Rechercher des crypto-monnaies populaires
            crypto_ids = {
                'ethereum': 'ethereum',
                'eth': 'ethereum',
                'cardano': 'cardano',
                'solana': 'solana',
                'polkadot': 'polkadot',
                'chainlink': 'chainlink',
                'litecoin': 'litecoin',
                'ltc': 'litecoin'
            }
            
            crypto_id = None
            for key, value in crypto_ids.items():
                if key in query.lower():
                    crypto_id = value
                    break
            
            if not crypto_id:
                return "Crypto-monnaie non reconnue. Essayez : Bitcoin, Ethereum, Cardano, Solana, etc."
            
            response = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd,eur&include_24hr_change=true",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                crypto_data = data.get(crypto_id, {})
                
                price_usd = crypto_data.get('usd', 'N/A')
                price_eur = crypto_data.get('eur', 'N/A')
                change_24h = crypto_data.get('usd_24h_change', 'N/A')
                
                change_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
                
                return f"""💰 **Prix de {crypto_id.title()} en temps réel** {change_emoji}

💵 **USD** : ${price_usd:,.2f}
💶 **EUR** : €{price_eur:,.2f}
📊 **Variation 24h** : {change_24h:+.2f}%

🕐 Mis à jour : {datetime.now().strftime('%H:%M:%S')}

*Source : CoinGecko API*"""
            
            else:
                return f"Impossible de récupérer les informations sur {crypto_id}. Veuillez réessayer plus tard."
                
        except Exception as e:
            return f"Erreur lors de la récupération des informations crypto : {str(e)}"
    
    @staticmethod
    def _general_search(query: str, max_results: int) -> str:
        """Recherche générale avec une API externe."""
        try:
            # Utiliser l'API de recherche de Brave (gratuite avec limite)
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'User-Agent': 'RAG-Analyst/1.0'
            }
            
            # Pour les recherches générales, utiliser une API de news
            if any(word in query.lower() for word in ['actualité', 'news', 'nouvelle', 'dernière']):
                response = requests.get(
                    f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&pageSize={max_results}",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articles', [])
                    
                    if articles:
                        formatted_results = []
                        for i, article in enumerate(articles[:max_results], 1):
                            formatted_results.append(
                                f"{i}. **{article['title']}**\n"
                                f"   {article['description']}\n"
                                f"   Source: {article['url']}\n"
                                f"   Publié: {article['publishedAt'][:10]}"
                            )
                        
                        return "\n\n".join(formatted_results)
            
            # Fallback : réponse générique basée sur la requête
            return f"""Recherche web pour : "{query}"

🔍 **Informations générales** :
- Cette requête nécessite une recherche web spécialisée
- Pour les prix crypto : utilisez "prix bitcoin" ou "prix ethereum"
- Pour les actualités : ajoutez "actualité" ou "news" à votre recherche

💡 **Suggestions** :
- "prix bitcoin aujourd'hui"
- "actualité IA 2024"
- "news technologie"

*Recherche web générale temporairement limitée*"""
                
        except Exception as e:
            return f"Erreur lors de la recherche générale : {str(e)}"


class DateTimeTool:
    """Outil pour obtenir la date et l'heure actuelles."""
    
    name = "current_datetime"
    description = """Outil pour obtenir la date et l'heure actuelles.
    Utile pour répondre à des questions comme "Quelle date sommes-nous ?"
    ou "Quelle heure est-il ?"
    """
    
    @staticmethod
    def run(format: str = "full") -> str:
        """Retourne la date/heure actuelle."""
        try:
            now = datetime.now()
            
            if format == "date":
                return now.strftime("%d/%m/%Y")
            elif format == "time":
                return now.strftime("%H:%M:%S")
            else:  # full
                return now.strftime("%d/%m/%Y %H:%M:%S")
                
        except Exception as e:
            logger.error("DateTime tool error", error=str(e))
            return f"Erreur : {str(e)}"


class DocumentQueryTool:
    """Outil pour interroger les documents de la session."""
    
    name = "document_query"
    description = """Outil pour interroger les documents PDF de la session courante.
    Utilise le système RAG pour trouver des informations dans les documents uploadés.
    Exemple d'entrée : "Quel est le chiffre d'affaires mentionné dans le document ?"
    """
    
    def __init__(self, rag_pipeline=None):
        self.rag_pipeline = rag_pipeline
    
    def run(self, query: str) -> str:
        """Interroge les documents de la session."""
        try:
            if not self.rag_pipeline or not self.rag_pipeline.qa_chain:
                return "Aucun document n'a été chargé dans cette session. Veuillez d'abord uploader des documents PDF."
            
            # Utiliser le pipeline RAG existant
            result = self.rag_pipeline.ask_question(query, save_conversation=False)
            
            # Formater la réponse avec les sources
            response = f"Réponse basée sur les documents :\n{result['answer']}\n\n"
            
            if result['sources']:
                response += f"Sources : {len(result['sources'])} passage(s) pertinent(s) trouvé(s)."
            
            logger.info("Document query executed", query=query[:50])
            return response
            
        except Exception as e:
            logger.error("Document query error", query=query[:50], error=str(e))
            return f"Erreur lors de la recherche dans les documents : {str(e)}"


class TextAnalysisTool:
    """Outil d'analyse de texte."""
    
    name = "text_analysis"
    description = """Outil pour analyser du texte : compter les mots, caractères, extraire des emails, URLs, etc.
    Exemple d'entrée : "Analyser : Le prix est de 100 euros. Contact: test@example.com"
    """
    
    @staticmethod
    def run(text: str) -> str:
        """Analyse un texte."""
        try:
            # Statistiques basiques
            word_count = len(text.split())
            char_count = len(text)
            line_count = len(text.split('\n'))
            
            # Extraction d'emails
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            
            # Extraction d'URLs
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
            
            # Extraction de nombres
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
            
            result = f"""Analyse du texte :
- Mots : {word_count}
- Caractères : {char_count}
- Lignes : {line_count}
- Emails trouvés : {len(emails)} {emails if emails else ''}
- URLs trouvées : {len(urls)} {urls if urls else ''}
- Nombres trouvés : {len(numbers)} {numbers[:10] if numbers else '(aucun)'}
"""
            
            logger.info("Text analysis executed", word_count=word_count)
            return result
            
        except Exception as e:
            logger.error("Text analysis error", error=str(e))
            return f"Erreur lors de l'analyse : {str(e)}"


# Liste de tous les outils disponibles
def get_all_tools(rag_pipeline=None):
    """Retourne tous les outils disponibles pour l'agent."""
    tools = [
        CalculatorTool(),
        WebSearchTool(),
        DateTimeTool(),
        TextAnalysisTool(),
    ]
    
    # Ajouter l'outil de requête document seulement si un pipeline RAG est disponible
    if rag_pipeline:
        tools.append(DocumentQueryTool(rag_pipeline))
    
    return tools

