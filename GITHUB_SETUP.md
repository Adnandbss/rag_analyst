# 📋 Guide : Push du Projet sur GitHub

## ✅ Étape 1 : Commits Locaux (TERMINÉ)

Vos fichiers sont déjà commités localement avec succès ! 🎉

**47 fichiers** ont été ajoutés au dépôt Git local.

---

## 🔗 Étape 2 : Créer un Repository sur GitHub

### Option A : Via l'interface web GitHub

1. **Connectez-vous** à GitHub.com avec votre compte
2. **Cliquez** sur le bouton "New" ou allez sur : https://github.com/new
3. **Remplissez** les informations :
   - **Repository name** : `rag-analyst` (ou le nom de votre choix)
   - **Description** : "RAG-Analyst Elite - Document Analysis Platform with AI Agents"
   - **Visibilité** : Public ou Private (selon vos préférences)
   - ⚠️ **IMPORTANT** : NE PAS cocher "Add a README file"
4. **Cliquez** sur "Create repository"

### Option B : Via GitHub CLI (si installé)

```bash
gh repo create rag-analyst --public --source=. --remote=origin --push
```

---

## 📤 Étape 3 : Connecter votre dépôt local à GitHub

Une fois votre repository créé sur GitHub, copiez l'URL :

**Format HTTPS :** `https://github.com/VOTRE_USERNAME/rag-analyst.git`  
**Format SSH :** `git@github.com:VOTRE_USERNAME/rag-analyst.git`

### Ensuite, dans votre terminal :

```bash
# Naviguez vers votre projet
cd C:\Users\000022483\Documents\rag_analyst

# Ajoutez le remote (remplacez VOTRE_USERNAME par votre username GitHub)
git remote add origin https://github.com/VOTRE_USERNAME/rag-analyst.git

# Push vers GitHub
git push -u origin master
```

**Note :** Si votre branche s'appelle `main` au lieu de `master` :
```bash
git branch -M main
git push -u origin main
```

---

## 🔐 Étape 4 : Authentification GitHub

GitHub peut demander une authentification. Deux options :

### Option A : Personal Access Token (RECOMMANDÉ)

1. Allez sur : https://github.com/settings/tokens
2. Cliquez sur "Generate new token (classic)"
3. Donnez un nom : "rag-analyst"
4. Sélectionnez la portée : **repo** (donne accès aux repositories)
5. Cliquez sur "Generate token"
6. **Copiez le token** (vous ne le reverrez plus !)
7. Utilisez-le comme mot de passe lors du `git push`

### Option B : GitHub CLI

```bash
gh auth login
```

---

## 📊 Commandes Complètes (Copier-Coller)

**Remplacez `VOTRE_USERNAME` par votre username GitHub :**

```bash
# Aller dans le projet
cd C:\Users\000022483\Documents\rag_analyst

# Ajouter le remote GitHub
git remote add origin https://github.com/VOTRE_USERNAME/rag-analyst.git

# Renommer la branche si nécessaire
git branch -M main

# Push vers GitHub
git push -u origin main
```

---

## ✅ Vérification

Une fois le push terminé, vérifiez sur :
`https://github.com/VOTRE_USERNAME/rag-analyst`

Vous devriez voir tous vos fichiers ! 🎉

---

## 📥 Récupérer sur votre Autre PC

### Sur votre autre PC :

```bash
# Cloner le repository
git clone https://github.com/VOTRE_USERNAME/rag-analyst.git

# Aller dans le dossier
cd rag-analyst

# Installer les dépendances
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Créer le fichier .env
copy .env.example .env
# Puis éditer .env avec votre clé OpenAI

# Lancer l'application
python -m uvicorn app.main:app --reload
```

---

## 🛠️ Commandes Utiles

### Voir l'état actuel :
```bash
git status
```

### Voir les commits :
```bash
git log --oneline
```

### Ajouter des modifications futures :
```bash
git add .
git commit -m "Description des changements"
git push
```

### Mettre à jour depuis GitHub :
```bash
git pull
```

---

## ⚠️ Fichiers Importants à NE PAS Oublier

✅ **Déjà gérés par .gitignore :**
- `.env` (clés secrètes)
- `venv/` (environnement virtuel)
- `*.sqlite3` (bases de données locales)
- `chroma_db/` (vecteurs locaux)

✅ **À ne PAS commit :**
- Votre clé API OpenAI (dans `.env`)
- Données sensibles

---

## 🎉 C'est Prêt !

Une fois ces étapes effectuées, vous pourrez :
- ✅ Récupérer le projet sur n'importe quel PC
- ✅ Partager votre code facilement
- ✅ Avoir un backup de votre travail
- ✅ Ajouter le projet à votre CV/LinkedIn

**Bon courage avec votre repository GitHub !** 🚀
