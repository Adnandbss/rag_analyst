"""
Processeur multi-modal pour extraire et analyser images et tableaux des PDFs.
Support de GPT-4 Vision pour l'analyse d'images.
"""

from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
from pathlib import Path
import structlog
from langchain_openai import ChatOpenAI

logger = structlog.get_logger(__name__)

class MultiModalProcessor:
    """Processeur pour extraire et analyser le contenu multi-modal des PDFs."""
    
    def __init__(self, use_vision_api: bool = False):
        """
        Initialise le processeur multi-modal.
        
        Args:
            use_vision_api: Utiliser GPT-4 Vision pour l'analyse (coûteux)
        """
        self.use_vision_api = use_vision_api
        
        if use_vision_api:
            self.vision_llm = ChatOpenAI(model_name="gpt-4-vision-preview", max_tokens=500)
        else:
            self.vision_llm = None
        
        logger.info("MultiModal processor initialized", use_vision=use_vision_api)

    def extract_images_from_pdf(self, pdf_path: str, output_dir: str = None) -> List[Dict[str, Any]]:
        """
        Extrait toutes les images d'un PDF.
        
        Args:
            pdf_path: Chemin vers le PDF
            output_dir: Dossier où sauvegarder les images (optionnel)
            
        Returns:
            Liste de dictionnaires avec infos sur chaque image
        """
        images_info = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Créer l'objet Image PIL
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Informations sur l'image
                    image_info = {
                        "page": page_num + 1,
                        "index": img_index,
                        "width": image.width,
                        "height": image.height,
                        "format": image_ext,
                        "size_bytes": len(image_bytes)
                    }
                    
                    # Sauvegarder si demandé
                    if output_dir:
                        output_path = Path(output_dir) / f"page{page_num+1}_img{img_index}.{image_ext}"
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        image.save(output_path)
                        image_info["filepath"] = str(output_path)
                    
                    # Encoder en base64 pour transmission
                    buffered = io.BytesIO()
                    image.save(buffered, format=image_ext.upper() if image_ext != "jpg" else "JPEG")
                    image_info["base64"] = base64.b64encode(buffered.getvalue()).decode()
                    
                    images_info.append(image_info)
            
            doc.close()
            
            logger.info("Images extracted from PDF",
                       pdf_path=pdf_path,
                       images_count=len(images_info))
            
            return images_info
            
        except Exception as e:
            logger.error("Image extraction failed", pdf_path=pdf_path, error=str(e))
            return []

    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extrait les tableaux d'un PDF.
        
        Args:
            pdf_path: Chemin vers le PDF
            
        Returns:
            Liste de tableaux avec leurs métadonnées
        """
        tables_info = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # PyMuPDF ne détecte pas nativement les tableaux
                # On utilise une heuristique basée sur le texte tabulaire
                tables = self._detect_tables_heuristic(page)
                
                for table_index, table_data in enumerate(tables):
                    table_info = {
                        "page": page_num + 1,
                        "index": table_index,
                        "rows": len(table_data),
                        "cols": len(table_data[0]) if table_data else 0,
                        "data": table_data
                    }
                    tables_info.append(table_info)
            
            doc.close()
            
            logger.info("Tables extracted from PDF",
                       pdf_path=pdf_path,
                       tables_count=len(tables_info))
            
            return tables_info
            
        except Exception as e:
            logger.error("Table extraction failed", pdf_path=pdf_path, error=str(e))
            return []

    def _detect_tables_heuristic(self, page) -> List[List[List[str]]]:
        """
        Détecte les tableaux avec une heuristique simple.
        Dans une vraie implémentation, utiliser tabula-py ou camelot.
        """
        # Placeholder - dans une vraie implémentation:
        # 1. Utiliser tabula-py ou camelot pour extraction de tables
        # 2. Ou analyser la structure du texte pour détecter les alignements
        return []

    def analyze_image_with_vision(self, image_base64: str, prompt: str = None) -> str:
        """
        Analyse une image avec GPT-4 Vision.
        
        Args:
            image_base64: Image encodée en base64
            prompt: Prompt personnalisé (optionnel)
            
        Returns:
            Description de l'image
        """
        if not self.vision_llm:
            return "Vision API non activée. Activez use_vision_api=True pour utiliser GPT-4 Vision."
        
        try:
            default_prompt = "Décris cette image en détail, en te concentrant sur les informations importantes pour l'analyse de documents d'entreprise."
            
            # Note: L'implémentation complète nécessiterait le format spécifique de GPT-4V
            # Ceci est un placeholder
            
            logger.info("Image analysis with vision API", prompt=prompt[:50] if prompt else "default")
            
            # Placeholder - vraie implémentation nécessite le bon format pour GPT-4V
            return "Analyse d'image avec GPT-4 Vision (implémentation à compléter)"
            
        except Exception as e:
            logger.error("Vision API analysis failed", error=str(e))
            return f"Erreur lors de l'analyse : {str(e)}"

    def process_multimodal_document(self, pdf_path: str) -> Dict[str, Any]:
        """
        Traite un document PDF en extrayant tout le contenu multi-modal.
        
        Args:
            pdf_path: Chemin vers le PDF
            
        Returns:
            Dictionnaire avec tout le contenu extrait
        """
        logger.info("Starting multimodal processing", pdf_path=pdf_path)
        
        # Extraire les images
        images = self.extract_images_from_pdf(pdf_path)
        
        # Extraire les tableaux
        tables = self.extract_tables_from_pdf(pdf_path)
        
        # Analyser les images avec Vision API si activé
        if self.use_vision_api and images:
            for img in images[:3]:  # Limiter à 3 images pour éviter les coûts
                description = self.analyze_image_with_vision(img["base64"][:100])  # Placeholder
                img["ai_description"] = description
        
        result = {
            "pdf_path": pdf_path,
            "images_count": len(images),
            "tables_count": len(tables),
            "images": images,
            "tables": tables,
            "has_visual_content": len(images) > 0 or len(tables) > 0
        }
        
        logger.info("Multimodal processing completed",
                   pdf_path=pdf_path,
                   images=len(images),
                   tables=len(tables))
        
        return result


class QueryExpander:
    """Expandeur de requêtes avec synonymes et termes liés."""
    
    def __init__(self):
        self.synonym_dict = {
            "chiffre d'affaires": ["CA", "revenus", "ventes", "recettes"],
            "bénéfice": ["profit", "résultat net", "gains"],
            "risque": ["danger", "menace", "vulnérabilité", "exposition"],
            "stratégie": ["plan", "approche", "tactique", "vision"],
            "croissance": ["développement", "expansion", "augmentation"],
            "innovation": ["R&D", "recherche", "développement", "nouveauté"],
            "partenariat": ["collaboration", "alliance", "accord", "joint-venture"],
            "concurrent": ["compétiteur", "rival", "adversaire"],
            "client": ["consommateur", "acheteur", "utilisateur"],
            "employé": ["salarié", "collaborateur", "personnel", "effectif"]
        }

    def expand_with_synonyms(self, query: str) -> List[str]:
        """
        Expands la query en ajoutant des synonymes.
        
        Args:
            query: Question originale
            
        Returns:
            Liste de variations avec synonymes
        """
        variations = [query]
        query_lower = query.lower()
        
        for term, synonyms in self.synonym_dict.items():
            if term in query_lower:
                for synonym in synonyms:
                    variation = query_lower.replace(term, synonym)
                    if variation != query_lower:
                        variations.append(variation.capitalize())
        
        return list(set(variations))  # Supprimer les doublons


# Instances globales
multimodal_processor = MultiModalProcessor(use_vision_api=False)
query_expander = QueryExpander()

