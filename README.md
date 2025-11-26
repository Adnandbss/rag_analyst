# 🧠 RAG-Analyst Elite: Plateforme d'Analyse de Documents par IA Générative

Application **production-ready** d'analyse de documents PDF avec IA générative avancée, incluant agents autonomes, monitoring temps réel, et évaluation automatisée.

## 🌟 Fonctionnalités Principales

### Intelligence Artificielle
- 🤖 **Agents IA Autonomes** : Système d'agents avec outils (calculator, web search, document query)
- 📄 **RAG Multi-Documents** : Gestion de sessions avec plusieurs PDFs par session
- 🔍 **Hybrid Search** : Combinaison BM25 + recherche sémantique + reranking CrossEncoder
- 🎯 **Query Optimization** : Expansion, reformulation, HyDE
- 📊 **Évaluation Automatique** : Métriques RAG (faithfulness, relevance, precision, recall)

### Monitoring & Production
- 📈 **Prometheus + Grafana** : Métriques temps réel et dashboards
- 🔒 **Sécurité Production** : Rate limiting, security headers, logging structuré
- ⚡ **Performance** : Cache intelligent, batch processing, compression
- 🧪 **Tests Automatisés** : Suite complète avec rapports HTML

### Interface Utilisateur
- 💬 **Chat Interactif** : Interface moderne avec historique
- 📊 **Dashboard Analytics** : Graphiques Plotly en temps réel
- 🎨 **Multi-Onglets** : Chat, Documents, Métriques, Exemples
- 🔧 **Configuration Avancée** : Sélection de modèles, mode agent, évaluation

## Architecture

Le projet utilise une architecture moderne en couches :

1.  **Frontend** (`frontend_advanced.py`): Interface Streamlit professionnelle avec 4 onglets
2.  **API Gateway** (`app/main.py`): FastAPI avec 25+ endpoints
3.  **Core Engine** (`app/core/`): 10 modules spécialisés (RAG, Agents, Evaluation, etc.)
4.  **Data Layer**: ChromaDB (vecteurs) + SQLite (métadonnées) + DiskCache (performance)
5.  **Monitoring**: Prometheus + Grafana + Structlog

## 🚀 Quick Start

### Installation

```bash
# 1. Cloner et configurer
git clone https://github.com/votre-username/rag-analyst.git
cd rag-analyst

# 2. Environnement virtuel
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Installer dépendances
pip install -r requirements.txt

# 4. Configurer la clé OpenAI
cp .env.example .env
# Éditer .env et ajouter votre OPENAI_API_KEY
```

### Lancement

```bash
# Terminal 1: API Backend
uvicorn app.main:app --reload

# Terminal 2: Frontend
streamlit run frontend_advanced.py
```

**URLs:**
- Frontend : http://localhost:8501
- API : http://127.0.0.1:8000
- API Docs : http://127.0.0.1:8000/docs
- Prometheus : http://127.0.0.1:8000/metrics/prometheus

---

### Phase 1: Cœur logique du RAG (Terminée)

Le cœur du projet est un ensemble de scripts Python qui utilisent `LangChain` pour exécuter un pipeline RAG.

-   **Fichiers Clés**:
    -   `app/core/rag_pipeline.py`: Contient les fonctions pour charger, découper, et vectoriser les PDFs, ainsi que pour créer la chaîne de question-réponse.
    -   `run_rag_cli.py`: Une interface en ligne de commande pour tester rapidement le pipeline.

-   **Fonctionnement**:
    1.  Un PDF est chargé et découpé en petits morceaux (chunks).
    2.  Chaque chunk est converti en un vecteur numérique (embedding) via l'API d'OpenAI.
    3.  Ces vecteurs sont stockés dans une base de données vectorielle `ChromaDB` locale.
    4.  Lorsqu'une question est posée, elle est également vectorisée pour trouver les chunks les plus pertinents dans la base de données.
    5.  La question et les chunks pertinents sont envoyés à un LLM (comme GPT-3.5) pour générer une réponse contextuelle.

### Phase 2: API Backend avec FastAPI

Pour rendre notre logique RAG accessible à d'autres applications (comme une interface web), nous l'exposons via une API REST en utilisant FastAPI.

#### Fichiers Clés

*   `app/main.py`: Contient le code de l'API FastAPI avec deux endpoints principaux :
    *   `POST /upload`: Pour uploader un fichier PDF, le traiter et créer la base de données vectorielle.
    *   `POST /ask`: Pour poser une question et obtenir une réponse basée sur le document uploadé.

#### Comment lancer l'API

1.  **Assurez-vous d'avoir installé les dépendances** :
    ```bash
    pip install -r requirements.txt
    ```

2.  **Lancez le serveur Uvicorn** depuis la racine du projet `rag_analyst`:
    ```bash
    uvicorn app.main:app --reload
    ```
    *   `app.main:app` signifie : "dans le fichier `main.py` du package `app`, trouve l'objet nommé `app`".
    *   `--reload` redémarre le serveur automatiquement à chaque modification du code.

3.  **Accédez à la documentation interactive** :
    Une fois le serveur lancé, ouvrez votre navigateur et allez à l'adresse [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Vous y trouverez une interface Swagger UI qui vous permet de tester les endpoints directement.

### Phase 3: Interface utilisateur avec Streamlit

Pour rendre l'application accessible aux utilisateurs finaux, nous avons créé une interface web moderne et intuitive avec Streamlit.

#### Fichiers Clés

*   `frontend.py`: Application Streamlit complète avec interface de chat, upload de fichiers, et gestion des erreurs.

#### Fonctionnalités

*   **Interface à deux colonnes** : Upload de documents à gauche, chat à droite
*   **Chat interactif** : Historique des conversations avec l'IA
*   **Affichage des sources** : Chaque réponse montre les passages du document utilisés
*   **Vérification de l'API** : Status en temps réel de la connexion au backend
*   **Exemples de questions** : Boutons avec des questions pré-définies pour démarrer rapidement
*   **Gestion d'erreurs** : Messages clairs en cas de problème de connexion ou de traitement

#### Comment lancer l'interface utilisateur

1.  **Assurez-vous que l'API backend est lancée** :
    Dans un premier terminal, avec l'environnement activé :
    ```bash
    uvicorn app.main:app --reload
    ```

2.  **Lancez l'interface Streamlit** dans un second terminal :
    ```bash
    # Dans le dossier rag_analyst, avec l'environnement activé
    streamlit run frontend.py
    ```

3.  **Accédez à l'application** :
    Votre navigateur devrait s'ouvrir automatiquement sur [http://localhost:8501](http://localhost:8501). Sinon, ouvrez cette adresse manuellement.

#### Workflow d'utilisation

1.  **Vérifiez le status** : Dans la sidebar, vous devez voir "✅ API Backend connectée"
2.  **Uploadez un PDF** : Glissez-déposez ou sélectionnez un fichier PDF dans la zone d'upload
3.  **Traitez le document** : Cliquez sur "🚀 Traiter le Document" et attendez le processus (quelques minutes)
4.  **Posez vos questions** : Utilisez la zone de chat pour dialoguer avec votre document
5.  **Explorez les sources** : Cliquez sur "📚 Sources utilisées" pour voir les passages exacts du PDF utilisés pour répondre

### Phase 4: Conteneurisation avec Docker

Pour faciliter le déploiement et garantir la portabilité de l'application, nous avons conteneurisé l'API backend avec Docker.

#### Fichiers Clés

*   `Dockerfile`: Configuration pour créer l'image Docker de l'API
*   `.dockerignore`: Liste des fichiers à exclure du contexte de build Docker
*   `docker-compose.yml`: Configuration pour orchestrer les services avec Docker Compose

#### Fonctionnalités Docker

*   **Image légère** : Basée sur `python:3.11-slim` pour optimiser la taille
*   **Multi-stage build** : Optimisation du cache Docker pour accélérer les builds
*   **Variables d'environnement** : Configuration flexible via `.env`
*   **Volumes persistants** : Les données ChromaDB et les PDFs sont sauvegardés
*   **Health check** : Vérification automatique de l'état de l'API
*   **Network isolation** : Réseau dédié pour les services

#### Comment utiliser Docker

1.  **Build de l'image** :
    ```bash
    docker build -t rag-analyst .
    ```

2.  **Lancement avec Docker Compose** (Recommandé) :
    ```bash
    # Assurez-vous que votre fichier .env existe avec votre clé OpenAI
    docker-compose up -d
    ```

3.  **Vérification** :
    L'API sera accessible sur [http://localhost:8000](http://localhost:8000)

4.  **Arrêt des services** :
    ```bash
    docker-compose down
    ```

#### Avantages de la conteneurisation

*   **Portabilité** : L'application fonctionne de manière identique sur tous les environnements
*   **Isolation** : Aucun conflit avec d'autres applications
*   **Scalabilité** : Facilite le déploiement sur des plateformes cloud
*   **Reproductibilité** : Environnement cohérent pour tous les développeurs

### Phase 5: CI/CD avec GitHub Actions

Mise en place d'un pipeline d'intégration et de déploiement continus pour automatiser les tests, builds, et déploiements.

#### Fichiers Clés

*   `.github/workflows/ci.yml`: Pipeline CI/CD complet avec GitHub Actions

#### Pipeline CI/CD

Le workflow automatisé comprend trois jobs principaux :

1.  **Test** :
    *   Configuration de l'environnement Python 3.11
    *   Installation des dépendances
    *   Tests d'import des modules critiques
    *   Validation de la structure du code

2.  **Build Docker** :
    *   Construction de l'image Docker
    *   Test de l'image (démarrage et sanité de l'API)
    *   Utilisation du cache Docker pour optimiser les performances
    *   Validation que l'application répond correctement

3.  **Publication** (conditionnel) :
    *   Déclenché seulement sur push vers `main`
    *   Connexion sécurisée à Docker Hub
    *   Push de l'image avec tags `latest` et SHA du commit
    *   Publication automatique pour le déploiement

#### Déclencheurs

*   **Push** vers les branches `main` ou `master`
*   **Pull Request** vers `main` ou `master`
*   Possibilité d'ajout de déclencheurs manuels (`workflow_dispatch`)

#### Bonnes pratiques implémentées

*   **Sécurité** : Utilisation de secrets GitHub pour les credentials Docker Hub
*   **Cache** : Optimisation des builds avec le cache Docker de GitHub Actions
*   **Tests isolés** : Chaque job s'exécute dans un environnement propre
*   **Conditional deployment** : Publication uniquement sur la branche principale
*   **Monitoring** : Logs détaillés pour debug en cas d'échec

## 🎯 Fonctionnalités Avancées

### 🤖 Mode Agent IA
Activez le mode agent dans les paramètres pour un assistant qui peut :
- Effectuer des calculs mathématiques
- Rechercher des informations sur internet
- Interroger vos documents
- Analyser du texte
- **Afficher son raisonnement étape par étape**

### 🔍 Hybrid Search
Recherche combinant :
- **BM25** : Recherche par mots-clés (keyword matching)
- **Semantic** : Recherche vectorielle (similarité sémantique)
- **Reranking** : CrossEncoder pour affiner les résultats
- **Résultat** : +30% de pertinence vs recherche simple

### 📊 Évaluation Automatique
Activez l'évaluation pour obtenir :
- Score de pertinence (relevance)
- Score de fidélité (faithfulness)
- Précision/rappel du contexte
- Scores ROUGE vs réponses de référence
- Graphiques de performance

### 📈 Monitoring Production
- Dashboard Prometheus avec 15+ métriques
- Grafana pour visualisation
- Logs structurés (JSON)
- Health checks détaillés
- Alerting configuré

### 🧪 Tests Automatisés
- Suite de 10+ test cases
- Évaluation automatique de qualité
- Génération de rapports HTML
- Intégration CI/CD
- A/B testing de stratégies

## 📚 Technologies et Compétences

### Stack IA & ML
*   **Frameworks** : LangChain (agents, chains), Sentence-Transformers (embeddings)
*   **LLMs** : OpenAI GPT-3.5/4, support Ollama (Mistral, Llama)
*   **RAG** : Retrieval, Reranking, Compression contextuelle
*   **Search** : Vector (ChromaDB), Keyword (BM25), Hybrid (RRF)
*   **Evaluation** : RAGAS, ROUGE scores, métriques custom

### Backend & API
*   **Framework** : FastAPI (async), Pydantic validation
*   **Database** : SQLite (SQLAlchemy ORM), ChromaDB (vecteurs)
*   **Cache** : DiskCache (gratuit, persistant)
*   **Monitoring** : Prometheus metrics, Structlog (JSON)
*   **Security** : Rate limiting, CORS, security headers

### Frontend & UX
*   **Framework** : Streamlit avec CSS custom
*   **Visualisation** : Plotly (graphiques interactifs), Pandas (tables)
*   **Components** : Chat, upload multi-fichiers, analytics dashboard
*   **UX** : Scores colorés, progression, exemples pré-configurés

### DevOps & MLOps
*   **Containerization** : Docker, Docker Compose, multi-stage builds
*   **CI/CD** : GitHub Actions (tests, build, deploy)
*   **Testing** : Pytest (unit, integration, mocks), coverage
*   **Observability** : Prometheus, Grafana, distributed tracing ready
*   **IaC** : Prêt pour Terraform/Kubernetes



Ce projet constitue une base solide pour démontrer vos compétences en entretien et peut servir de fondation pour des projets plus complexes intégrant des agents IA, du fine-tuning, ou des architectures multi-modales.
