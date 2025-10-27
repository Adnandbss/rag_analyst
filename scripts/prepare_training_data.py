"""
Script pour préparer les données d'entraînement pour le fine-tuning.
"""

import sys
import json
from pathlib import Path
import argparse

# Ajouter le dossier parent au path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import get_db, Conversation


def collect_conversations(min_confidence: float = 0.7, max_count: int = None):
    """
    Collecte les conversations depuis la base de données.
    
    Args:
        min_confidence: Score de confiance minimum
        max_count: Nombre maximum de conversations à collecter
    """
    db = next(get_db())
    
    try:
        query = db.query(Conversation).filter(
            Conversation.confidence_score >= min_confidence
        ).order_by(Conversation.confidence_score.desc())
        
        if max_count:
            query = query.limit(max_count)
        
        conversations = query.all()
        
        print(f"✓ {len(conversations)} conversations collectées")
        return conversations
        
    finally:
        db.close()


def format_for_openai(conversations):
    """
    Formate les conversations au format requis par OpenAI.
    """
    training_data = []
    
    system_message = """Tu es un assistant expert en analyse de documents financiers et rapports d'entreprise. 
Tu fournis des réponses précises, factuelles et bien structurées basées uniquement sur les informations des documents fournis."""
    
    for conv in conversations:
        training_data.append({
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": conv.question},
                {"role": "assistant", "content": conv.answer}
            ]
        })
    
    return training_data


def save_as_jsonl(data, output_file: str):
    """Sauvegarde les données au format JSONL."""
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in data:
            json_line = json.dumps(item, ensure_ascii=False)
            f.write(json_line + '\n')
    
    print(f"✓ Dataset sauvegardé : {output_file}")


def split_train_test(data, test_ratio: float = 0.2):
    """Divise le dataset en train/test."""
    split_index = int(len(data) * (1 - test_ratio))
    
    return data[:split_index], data[split_index:]


def print_statistics(data):
    """Affiche des statistiques sur le dataset."""
    if not data:
        print("Dataset vide")
        return
    
    # Longueur des questions
    question_lengths = [len(item["messages"][1]["content"]) for item in data]
    avg_q_length = sum(question_lengths) / len(question_lengths)
    
    # Longueur des réponses
    answer_lengths = [len(item["messages"][2]["content"]) for item in data]
    avg_a_length = sum(answer_lengths) / len(answer_lengths)
    
    # Estimation des tokens (1 token ≈ 4 chars)
    total_tokens = (sum(question_lengths) + sum(answer_lengths)) / 4
    
    print("\n=== Statistiques du Dataset ===")
    print(f"Nombre d'exemples : {len(data)}")
    print(f"Longueur moyenne des questions : {avg_q_length:.0f} caractères")
    print(f"Longueur moyenne des réponses : {avg_a_length:.0f} caractères")
    print(f"Tokens estimés : {total_tokens:,.0f}")
    print(f"Coût estimé (3 epochs, GPT-3.5): ${(total_tokens / 1000) * 0.008 * 3:.2f}")


def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(description="Préparer les données pour fine-tuning")
    parser.add_argument("--min-confidence", type=float, default=0.7, 
                       help="Score de confiance minimum")
    parser.add_argument("--max-count", type=int, default=None,
                       help="Nombre maximum de conversations")
    parser.add_argument("--output", type=str, default="fine_tuning_data.jsonl",
                       help="Fichier de sortie")
    parser.add_argument("--test-split", type=float, default=0.2,
                       help="Ratio pour le set de test")
    
    args = parser.parse_args()
    
    print("=== Préparation des Données de Fine-Tuning ===\n")
    
    # 1. Collecter les conversations
    print("1. Collecte des conversations...")
    conversations = collect_conversations(args.min_confidence, args.max_count)
    
    if not conversations:
        print("❌ Aucune conversation trouvée. Veuillez d'abord utiliser l'application.")
        return
    
    # 2. Formater pour OpenAI
    print("2. Formatage des données...")
    training_data = format_for_openai(conversations)
    
    # 3. Split train/test
    print("3. Division train/test...")
    train_data, test_data = split_train_test(training_data, args.test_split)
    print(f"   Train: {len(train_data)} exemples")
    print(f"   Test: {len(test_data)} exemples")
    
    # 4. Sauvegarder
    print("4. Sauvegarde des fichiers...")
    train_file = args.output.replace(".jsonl", "_train.jsonl")
    test_file = args.output.replace(".jsonl", "_test.jsonl")
    
    save_as_jsonl(train_data, train_file)
    save_as_jsonl(test_data, test_file)
    
    # 5. Statistiques
    print_statistics(train_data)
    
    print("\n✅ Préparation terminée!")
    print(f"\nFichiers générés :")
    print(f"  - {train_file}")
    print(f"  - {test_file}")
    print(f"\nProchaine étape : Uploader {train_file} sur OpenAI pour fine-tuning")


if __name__ == "__main__":
    main()

