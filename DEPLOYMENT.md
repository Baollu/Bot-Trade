# Guide de Déploiement en Production - Nexus Trade

Ce guide explique comment déployer Nexus Trade en production de manière sécurisée et performante.

## ⚠️ Important

**Ce système est conçu pour du trading simulé (paper trading). Pour du trading réel:**
- Consultez un conseiller financier
- Testez extensivement en simulation pendant des mois
- Commencez avec de très petites sommes
- Surveillez en permanence
- Préparez-vous à intervenir manuellement

## 🏗️ Architecture de Production

```
Internet
    ↓
[Load Balancer] (Nginx/HAProxy)
    ↓
[Nexus Trade App] × N (Replicas)
    ↓
[Redis Cluster] (High Availability)
    ↓
[PostgreSQL] (Primary/Replica)
    ↓
[Ethereum Node] (ou Alchemy/Infura)
```

## 📋 Checklist Pré-Déploiement

### Sécurité

- [ ] Utiliser HTTPS (certificat SSL/TLS)
- [ ] Activer l'authentification pour le dashboard
- [ ] Stocker les clés privées dans un vault (AWS KMS, HashiCorp Vault)
- [ ] Activer le pare-feu (UFW, iptables)
- [ ] Configurer fail2ban
- [ ] Limiter les IPs autorisées
- [ ] Scanner les dépendances (Dependabot, Snyk)

### Infrastructure

- [ ] Minimum 2 vCPU, 4GB RAM
- [ ] SSD pour PostgreSQL
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Logging centralisé (ELK, Loki)
- [ ] Backups automatiques
- [ ] Plan de disaster recovery

### Base de Données

- [ ] PostgreSQL en mode réplication
- [ ] Backups quotidiens
- [ ] Connection pooling (PgBouncer)
- [ ] Indexes optimisés
- [ ] Partitioning si > 10M rows

### Redis

- [ ] Redis Cluster ou Sentinel
- [ ] Persistence activée (AOF)
- [ ] Maxmemory policy configurée
- [ ] Réplication master-slave

## 🚀 Déploiement Docker

### 1. Variables d'Environnement de Production

```bash
# .env.production
DB_HOST=postgres-primary.internal
DB_PORT=5432
DB_USER=nexus_prod
DB_PASSWORD=<STRONG_PASSWORD>
DB_NAME=nexus_trade_prod

REDIS_HOST=redis-cluster.internal
REDIS_PORT=6379
REDIS_PASSWORD=<STRONG_PASSWORD>

SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/<YOUR_KEY>
PRIVATE_KEY=<STORED_IN_VAULT>

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090

# Logging
LOG_LEVEL=info
LOG_FORMAT=json
```

### 2. Docker Compose Production

```yaml
version: '3.8'

services:
  app:
    image: nexus-trade:latest
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    environment:
      - ENV=production
    env_file:
      - .env.production
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
```

### 3. Configuration Nginx

```nginx
upstream nexus_backend {
    least_conn;
    server app1:8080;
    server app2:8080;
    server app3:8080;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://nexus_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://nexus_backend/health;
    }
}
```

## 📊 Monitoring

### Prometheus Metrics

Le système expose des métriques sur `/metrics`:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'nexus-trade'
    static_configs:
      - targets: ['app:9090']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Alertes Recommandées

```yaml
groups:
  - name: nexus_alerts
    rules:
      - alert: HighLatency
        expr: prediction_latency_ms > 100
        for: 5m
        annotations:
          summary: "Latence IA trop élevée"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        annotations:
          summary: "PostgreSQL est down"

      - alert: LowBalance
        expr: portfolio_balance < 100
        annotations:
          summary: "Solde critique"
```

## 🔐 Gestion des Secrets

### AWS Secrets Manager

```go
import (
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/secretsmanager"
)

func getSecret(secretName string) (string, error) {
    sess := session.Must(session.NewSession())
    svc := secretsmanager.New(sess)
    
    result, err := svc.GetSecretValue(&secretsmanager.GetSecretValueInput{
        SecretId: aws.String(secretName),
    })
    
    return *result.SecretString, err
}
```

## 💾 Backups

### PostgreSQL

```bash
# Backup quotidien
0 2 * * * pg_dump -h localhost -U nexus_prod nexus_trade_prod | gzip > /backups/nexus_$(date +\%Y\%m\%d).sql.gz

# Rétention 30 jours
find /backups/ -name "nexus_*.sql.gz" -mtime +30 -delete
```

### Restauration

```bash
gunzip -c backup.sql.gz | psql -h localhost -U nexus_prod nexus_trade_prod
```

## 🔄 CI/CD

### GitHub Actions Deploy

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t nexus-trade:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker tag nexus-trade:${{ github.sha }} registry.example.com/nexus-trade:latest
          docker push registry.example.com/nexus-trade:latest
      
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/nexus-trade
            docker-compose pull
            docker-compose up -d
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Augmenter le nombre de replicas
docker-compose up --scale app=5
```

### Vertical Scaling

Augmenter les ressources machine:
- Plus de CPU pour l'inférence IA
- Plus de RAM pour Redis
- SSD plus rapides pour PostgreSQL

## 🧪 Tests de Charge

```bash
# Installer k6
brew install k6

# Test de charge
k6 run loadtest.js
```

```javascript
// loadtest.js
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '5m', target: 200 },
    { duration: '2m', target: 0 },
  ],
};

export default function () {
  let res = http.get('https://your-domain.com/api/dashboard');
  check(res, { 'status was 200': (r) => r.status == 200 });
}
```

## 🚨 Incident Response

### Procédure en Cas de Problème

1. **Alertes reçues** → Check Grafana/logs
2. **Identifier le problème** → Composant défaillant
3. **Rollback si nécessaire** → Version précédente
4. **Fix** → Déploiement correctif
5. **Post-mortem** → Documentation

### Contacts d'Urgence

- DevOps: [contact]
- DBA: [contact]
- Sécurité: [contact]

## 📝 Checklist de Mise en Production

- [ ] Tests de charge réussis
- [ ] Backups configurés et testés
- [ ] Monitoring actif
- [ ] Alertes configurées
- [ ] Documentation à jour
- [ ] Runbook d'incidents créé
- [ ] Certificats SSL valides
- [ ] Secrets sécurisés
- [ ] Logs centralisés
- [ ] Plan de rollback testé

---

**Note:** Ce guide est un point de départ. Adaptez-le à vos besoins spécifiques et contraintes de sécurité.
