# Guide de Déploiement - RAG Analyst

Ce guide couvre les différentes options de déploiement pour RAG-Analyst.

## Prérequis

- Python 3.11+
- Docker & Docker Compose (pour déploiement conteneurisé)
- Clé API OpenAI
- 2GB RAM minimum, 4GB recommandé
- 5GB espace disque

---

## Option 1 : Développement Local

### Installation

```bash
# 1. Cloner le repository
git clone https://github.com/votre-username/rag-analyst.git
cd rag-analyst

# 2. Créer l'environnement virtuel
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env et ajouter votre clé OpenAI
```

### Lancement

```bash
# Terminal 1 : API Backend
uvicorn app.main:app --reload

# Terminal 2 : Frontend Streamlit
streamlit run frontend_advanced.py
```

**URLs:**
- API : http://127.0.0.1:8000
- Frontend : http://localhost:8501
- Docs API : http://127.0.0.1:8000/docs

---

## Option 2 : Docker Local

### Configuration

```bash
# 1. Créer le fichier .env
echo "OPENAI_API_KEY=sk-..." > .env

# 2. Build et lancer
docker-compose up -d

# 3. Vérifier les logs
docker-compose logs -f

# 4. Arrêter
docker-compose down
```

**URLs:** Identiques à Option 1

### Troubleshooting Docker

```bash
# Rebuild forcé
docker-compose build --no-cache

# Voir les containers
docker ps

# Entrer dans un container
docker exec -it rag-analyst-api bash

# Nettoyer les volumes
docker-compose down -v
```

---

## Option 3 : Cloud Deployment (AWS)

### Architecture AWS Recommandée

```
Internet → ALB → ECS Fargate (API) → RDS PostgreSQL
                              ↓
                         S3 (PDFs) + ElastiCache Redis
                              ↓
                         CloudWatch (Monitoring)
```

### Étapes de Déploiement AWS

#### 1. Préparation

```bash
# Build et push l'image Docker
docker build -t rag-analyst:latest .
docker tag rag-analyst:latest <account>.dkr.ecr.<region>.amazonaws.com/rag-analyst:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/rag-analyst:latest
```

#### 2. Infrastructure as Code (Terraform)

```hcl
# Exemple de ressources Terraform
resource "aws_ecs_service" "rag_analyst" {
  name            = "rag-analyst-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.rag_analyst.arn
  desired_count   = 2
  
  load_balancer {
    target_group_arn = aws_lb_target_group.rag_analyst.arn
    container_name   = "rag-analyst-api"
    container_port   = 8000
  }
}

resource "aws_rds_instance" "postgres" {
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  db_name             = "rag_analyst"
}
```

#### 3. Variables d'Environnement AWS

```bash
# Dans ECS Task Definition
{
  "environment": [
    {"name": "OPENAI_API_KEY", "value": "..."},
    {"name": "DATABASE_URL", "value": "postgresql://..."},
    {"name": "REDIS_URL", "value": "redis://..."}
  ]
}
```

#### 4. Monitoring CloudWatch

- Activer logs CloudWatch pour ECS
- Créer des alarmes sur :
  - CPU > 80%
  - Memory > 80%
  - Error rate > 5%
  - Response time > 5s

---

## Option 4 : Google Cloud Platform

### Architecture GCP

```
Internet → Cloud Load Balancer → Cloud Run (API)
                                      ↓
                              Cloud SQL (PostgreSQL)
                                      ↓
                              Cloud Storage (PDFs)
```

### Déploiement GCP

```bash
# 1. Build et push
gcloud builds submit --tag gcr.io/PROJECT_ID/rag-analyst

# 2. Deploy sur Cloud Run
gcloud run deploy rag-analyst \
  --image gcr.io/PROJECT_ID/rag-analyst \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=sk-...

# 3. Configurer Cloud SQL
gcloud sql instances create rag-analyst-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=europe-west1
```

---

## Option 5 : Azure

### Architecture Azure

```
Internet → Azure App Service → Azure Database for PostgreSQL
                                      ↓
                              Azure Blob Storage
                                      ↓
                              Application Insights
```

### Déploiement Azure

```bash
# 1. Créer les ressources
az group create --name rag-analyst-rg --location westeurope

az acr create --resource-group rag-analyst-rg \
  --name raganalyst --sku Basic

# 2. Build et push
az acr build --registry raganalyst \
  --image rag-analyst:latest .

# 3. Créer App Service
az webapp create \
  --resource-group rag-analyst-rg \
  --plan rag-analyst-plan \
  --name rag-analyst-app \
  --deployment-container-image-name raganalyst.azurecr.io/rag-analyst:latest

# 4. Configurer les variables
az webapp config appsettings set \
  --resource-group rag-analyst-rg \
  --name rag-analyst-app \
  --settings OPENAI_API_KEY=sk-...
```

---

## Configuration Production

### Variables d'Environnement Essentielles

```bash
# API Keys
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis (optionnel)
REDIS_URL=redis://host:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com

# Performance
MAX_WORKERS=4
TIMEOUT=60

# Monitoring
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO
```

### Checklist de Sécurité Production

- [ ] Changer toutes les clés secrètes par défaut
- [ ] Activer HTTPS (certificat SSL)
- [ ] Configurer un firewall
- [ ] Activer l'authentification JWT
- [ ] Limiter les CORS à vos domaines
- [ ] Configurer les backups automatiques
- [ ] Activer le monitoring et alerting
- [ ] Mettre en place un WAF
- [ ] Scanner les vulnérabilités (Snyk, Trivy)
- [ ] Chiffrer les données sensibles

### Optimisations Performance

```python
# Dans app/main.py
app = FastAPI(
    workers=4,                    # Multiple workers
    timeout_keep_alive=5,
    limit_concurrency=100,
    limit_max_requests=1000
)

# Connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

---

## Monitoring en Production

### Prometheus + Grafana Setup

```bash
# 1. Lancer Prometheus
docker run -d -p 9090:9090 \
  -v ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# 2. Lancer Grafana
docker run -d -p 3000:3000 grafana/grafana

# 3. Accéder à Grafana
# http://localhost:3000
# Login: admin / admin

# 4. Ajouter Prometheus comme data source
# URL: http://prometheus:9090

# 5. Importer le dashboard
# Utiliser monitoring/grafana-dashboard.json
```

### Logs Centralisés

#### Option 1 : ELK Stack
```bash
# Elasticsearch + Logstash + Kibana
docker-compose -f docker-compose.elk.yml up -d
```

#### Option 2 : Cloud Logging
- AWS CloudWatch
- Google Cloud Logging
- Azure Monitor

---

## Scaling Guide

### Scaling Vertical (1 → 100 users)
- Augmenter RAM/CPU
- Optimiser connection pooling
- Activer caching (Redis)

### Scaling Horizontal (100 → 10K users)
- Load balancer (Nginx, ALB)
- Multiple API instances
- Shared state (Redis)
- Queue système (Celery)

### Scaling Global (10K+ users)
- Multi-region deployment
- CDN pour assets
- Read replicas pour DB
- Caching agressif

---

## Backup & Recovery

### Backup Automatique

```bash
# Script de backup SQLite
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
sqlite3 rag_sessions.db ".backup 'backups/rag_sessions_$DATE.db'"

# Script de backup ChromaDB
tar -czf backups/chroma_db_$DATE.tar.gz chroma_db/
```

### Restoration

```bash
# Restore SQLite
cp backups/rag_sessions_20241013.db rag_sessions.db

# Restore ChromaDB
tar -xzf backups/chroma_db_20241013.tar.gz
```

---

## Troubleshooting

### Problème : API ne démarre pas

```bash
# Vérifier les logs
docker logs rag-analyst-api

# Vérifier les variables d'env
docker exec rag-analyst-api env | grep OPENAI
```

### Problème : Slow Response Times

1. Vérifier les métriques Prometheus
2. Activer le cache Redis
3. Optimiser le chunk size
4. Réduire k (nombre de documents retrieved)

### Problème : Out of Memory

1. Réduire le nombre de documents par session
2. Activer le garbage collection agressif
3. Utiliser des workers séparés
4. Augmenter la RAM

---

## Maintenance

### Tâches Régulières

- **Quotidien** : Vérifier les logs d'erreur
- **Hebdomadaire** : Analyser les métriques de performance
- **Mensuel** : Backup complet, mise à jour dépendances
- **Trimestriel** : Audit de sécurité, optimization review

---

## Support

Pour toute question de déploiement, consultez :
- GitHub Issues
- Documentation API : `/docs`
- Architecture : `ARCHITECTURE.md`

