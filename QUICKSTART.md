# ⚡ Guide de Démarrage Rapide - RAG-Analyst Elite

Ce guide vous permet de lancer l'application en **5 minutes**.

## 📋 Prérequis

- Python 3.11+
- Clé API OpenAI ([obtenir ici](https://platform.openai.com/api-keys))
- 4GB RAM minimum
- Windows/Mac/Linux

---

## 🚀 Installation Express (5 minutes)

### Étape 1 : Téléchargement (30 secondes)

```bash
git clone https://github.com/votre-username/rag-analyst.git
cd rag-analyst
```

### Étape 2 : Configuration (1 minute)

**Windows PowerShell:**
```powershell
# Créer environnement virtuel
python -m venv venv
.\venv\Scripts\activate

# Configurer proxy si nécessaire (entreprise)
$env:HTTP_PROXY="http://proxy:port"
$env:HTTPS_PROXY="http://proxy:port"

# Installer dépendances
pip install -r requirements.txt
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Étape 3 : Configuration OpenAI (30 secondes)

Créez le fichier `.env` :
```bash
# Windows
New-Item -Path .env -ItemType File
notepad .env

# Linux/Mac
nano .env
```

Ajoutez dedans :
```
OPENAI_API_KEY=sk-votre-cle-ici
```

**Sauvegardez et fermez.**

### Étape 4 : Lancement (1 minute)

**Terminal 1 - API Backend:**
```powershell
# Windows (avec clé dans environnement)
$env:OPENAI_API_KEY="sk-votre-cle"
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Linux/Mac
export OPENAI_API_KEY="sk-votre-cle"
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend (nouveau terminal):**
```powershell
# Windows
cd rag-analyst
.\venv\Scripts\activate
.\venv\Scripts\python.exe -m streamlit run frontend_advanced.py

# Linux/Mac
streamlit run frontend_advanced.py
```

### Étape 5 : Accès (10 secondes)

Votre navigateur s'ouvre automatiquement sur **http://localhost:8501**

✅ **C'est prêt !**

---

## 🎯 Premier Test (2 minutes)

### 1. Créer une Session
- Sidebar → "➕ Créer une nouvelle session"
- Nom : "Test Démo"
- Cliquez "Créer"

### 2. Uploader un PDF
- Onglet "📤 Documents"
- Sélectionnez un PDF (rapport, article, etc.)
- Cliquez "🚀 Traiter les Documents"
- Attendez 1-2 minutes

### 3. Poser des Questions

**Mode RAG Standard:**
```
"Résume ce document en 3 points"
"Quels sont les chiffres clés mentionnés ?"
```

**Mode Agent IA:**
- Activez "🤖 Mode Agent IA" dans la sidebar
- Testez :
```
"Quelle est la racine carrée de 144 ?"
"Cherche sur internet le prix du bitcoin aujourd'hui"
"Quelle date sommes-nous ?"
```

### 4. Voir les Métriques
- Onglet "📈 Métriques"
- Graphiques interactifs de performance

---

## 🐛 Résolution Rapide des Problèmes

### "API Backend non disponible"

**Solution 1:** Rafraîchissez la page (F5)

**Solution 2:** Vérifiez que l'API tourne
```bash
# Dans le navigateur:
http://127.0.0.1:8000/health
```

Si vous voyez du JSON, l'API marche. Si erreur de connexion, redémarrez l'API.

### "Module 'plotly' not found"

```bash
.\venv\Scripts\python.exe -m pip install plotly pandas
```

### Problème de proxy (entreprise)

```powershell
# Avant chaque commande pip, définir :
$env:HTTP_PROXY="http://proxy:port"
$env:HTTPS_PROXY="http://proxy:port"
```

### "The api_key client option must be set"

1. Vérifiez que le fichier `.env` existe et contient votre clé
2. Redémarrez l'API (elle charge `.env` au démarrage)
3. Ou définissez directement :
```powershell
$env:OPENAI_API_KEY="sk-votre-cle"
```

---

## 📊 URLs Importantes

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:8501 | Interface principale |
| **API Docs** | http://127.0.0.1:8000/docs | Documentation interactive |
| **Health Check** | http://127.0.0.1:8000/health | Statut du système |
| **Metrics** | http://127.0.0.1:8000/metrics | Métriques JSON |
| **Prometheus** | http://127.0.0.1:8000/metrics/prometheus | Format Prometheus |

---

## 🎥 Démo Recommandée (3 minutes)

### Script de Demo
1. **Intro** (20s) : "Voici RAG-Analyst, une plateforme d'analyse de documents par IA"
2. **Upload** (30s) : Créer session, uploader PDF
3. **RAG** (40s) : Poser 2 questions sur le document
4. **Agent** (60s) : Activer agent, montrer raisonnement avec outils
5. **Metrics** (30s) : Montrer dashboard avec graphiques
6. **Conclusion** (10s) : "Architecture production-ready, code sur GitHub"

---

## 📖 Documentation Complète

- **README.md** : Vue d'ensemble et tutoriels
- **ARCHITECTURE.md** : Décisions techniques et diagrammes
- **docs/API.md** : Documentation des 25 endpoints
- **docs/DEPLOYMENT.md** : Guide de déploiement cloud
- **PROJET_COMPLET.md** : Document de synthèse pour candidature

---

## 🎓 Ressources d'Apprentissage

Pour approfondir les concepts utilisés :

- **Agents IA** : [LangChain Agents Documentation](https://python.langchain.com/docs/modules/agents/)
- **RAG** : [Retrieval-Augmented Generation Paper](https://arxiv.org/abs/2005.11401)
- **Hybrid Search** : [BM25 + Vector Search](https://www.pinecone.io/learn/hybrid-search/)
- **MLOps** : [MLOps Principles](https://ml-ops.org/)
- **Prometheus** : [Prometheus Docs](https://prometheus.io/docs/introduction/overview/)

---

**Vous êtes prêt ! Lancez l'application et impressionnez les recruteurs.** 🚀

