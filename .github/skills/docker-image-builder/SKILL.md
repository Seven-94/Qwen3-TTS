---
name: docker-image-builder
description: Créer des images Docker optimisées et sécurisées en suivant les meilleures pratiques officielles de Docker. Utilisez cette skill pour créer des Dockerfiles, optimiser des images existantes, implémenter des multi-stage builds, configurer la sécurité, et assurer la maintenance d'images Docker pour tout type de projet (Python, Node.js, Go, Java, etc.).
license: Complete terms in LICENSE.txt
---

# Docker Image Builder

Cette skill vous guide dans la création d'images Docker optimisées et sécurisées en suivant les meilleures pratiques officielles.

## Quand utiliser cette skill

- Créer un Dockerfile pour un nouveau projet
- Optimiser une image Docker existante
- Implémenter des multi-stage builds
- Améliorer la sécurité des images
- Réduire la taille des images
- Configurer le caching efficacement
- Mettre en place un workflow CI/CD pour les images

## Workflow de base

### 1. Analyse du projet

Avant de créer un Dockerfile, identifiez :

- Le langage/framework principal (Python, Node.js, Go, Java, etc.)
- Les dépendances runtime nécessaires
- Les outils de build requis
- Les artefacts finaux à inclure
- Les ports à exposer
- Les volumes de données

### 2. Choisir l'image de base appropriée

**Ordre de préférence :**

1. **Images officielles Docker** (badge "Official Image")
2. **Verified Publisher** (fournisseurs vérifiés)
3. **Docker-Sponsored Open Source**

**Critères de sélection :**

- Privilégier les variantes `-slim` ou `-alpine` pour la production
- Utiliser une version complète pour le build (si multi-stage)
- Toujours spécifier une version explicite (ex: `python:3.11-slim` plutôt que `python:latest`)

Exemples d'images recommandées :

```dockerfile
# Python
FROM python:3.11-slim              # Production
FROM python:3.11                   # Build

# Node.js
FROM node:20-alpine                # Production
FROM node:20                       # Build

# Go
FROM golang:1.21-alpine            # Build
FROM alpine:3.19                   # Production (statique)

# Java
FROM eclipse-temurin:21-jre-alpine # Production
FROM eclipse-temurin:21-jdk        # Build
```

### 3. Implémenter un multi-stage build

**Structure recommandée :**

```dockerfile
# syntax=docker/dockerfile:1

# Stage 1: Build
FROM <base-build-image> AS builder
WORKDIR /build
# Copier et installer dépendances de build
# Compiler/build l'application

# Stage 2: Production
FROM <base-runtime-image>
WORKDIR /app
# Copier uniquement les artefacts nécessaires depuis builder
# Configurer l'utilisateur non-root
# Définir ENTRYPOINT/CMD
```

**Avantages :**

- Image finale plus légère (pas d'outils de build)
- Meilleure sécurité (surface d'attaque réduite)
- Séparation des préoccupations

### 4. Optimiser le caching des layers

**Règle d'or :** Ordonner les instructions de la moins changeante à la plus changeante

```dockerfile
# ✅ BON : Dépendances d'abord (changent rarement)
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# ❌ MAUVAIS : Invalide le cache à chaque modification du code
COPY . .
RUN pip install -r requirements.txt
```

### 5. Configurer la sécurité

**Toujours :**

- Créer et utiliser un utilisateur non-root
- Minimiser les privilèges
- Ne pas exposer de secrets dans les layers

```dockerfile
# Créer un utilisateur non-root
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Copier les fichiers et changer propriétaire
COPY --chown=appuser:appuser . /app

# Basculer vers l'utilisateur non-root
USER appuser
```

### 6. Utiliser .dockerignore

Créer un fichier `.dockerignore` pour exclure les fichiers inutiles :

```
# Contrôle de version
.git
.gitignore
.github

# Dépendances et cache
node_modules
__pycache__
*.pyc
.venv
venv

# Documentation
*.md
README*
docs/

# CI/CD
.gitlab-ci.yml
.travis.yml
Jenkinsfile

# Fichiers de développement
.vscode
.idea
*.log
.env
.DS_Store
```

## Checklist de qualité

Avant de finaliser votre Dockerfile, vérifiez :

- [ ] Utilisation d'une image de base officielle
- [ ] Version de l'image de base épinglée (avec digest si critique)
- [ ] Multi-stage build implémenté (si applicable)
- [ ] Ordre des layers optimisé pour le cache
- [ ] Utilisateur non-root configuré
- [ ] .dockerignore présent et complet
- [ ] Arguments multi-lignes triés alphabétiquement
- [ ] Absence de secrets dans les layers
- [ ] Instructions RUN combinées avec && quand pertinent
- [ ] Cleaning des caches de package managers
- [ ] Labels informatifs ajoutés
- [ ] Ports exposés correctement avec EXPOSE
- [ ] WORKDIR avec chemins absolus
- [ ] CMD ou ENTRYPOINT en format exec

## Instructions Dockerfile spécifiques

### RUN - Bonnes pratiques

**Combiner les commandes pour réduire les layers :**

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    package1 \
    package2 \
    package3 \
    && rm -rf /var/lib/apt/lists/*
```

**Trier les arguments alphabétiquement :**

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    python3 \
    && rm -rf /var/lib/apt/lists/*
```

**Nettoyer les caches :**

```dockerfile
# Debian/Ubuntu
RUN apt-get update && apt-get install -y packages \
    && rm -rf /var/lib/apt/lists/*

# Alpine
RUN apk add --no-cache packages

# Python
RUN pip install --no-cache-dir -r requirements.txt

# Node.js
RUN npm ci --only=production && npm cache clean --force
```

### COPY vs ADD

**Règle générale :** Utiliser `COPY` sauf si vous avez besoin des fonctionnalités spéciales d'`ADD`

```dockerfile
# ✅ Préférer COPY pour les fichiers locaux
COPY requirements.txt .
COPY src/ /app/src/

# ✅ Utiliser ADD pour télécharger et extraire
ADD --checksum=sha256:abc123... https://example.com/file.tar.gz /tmp/
```

### ENV - Variables d'environnement

```dockerfile
# Définir des versions pour faciliter la maintenance
ENV PYTHON_VERSION=3.11 \
    APP_HOME=/app \
    APP_USER=appuser

# Mettre à jour PATH
ENV PATH="${APP_HOME}/bin:${PATH}"
```

### EXPOSE - Ports

```dockerfile
# Documenter les ports utilisés
EXPOSE 8000/tcp
EXPOSE 9090/tcp
```

### CMD et ENTRYPOINT

**Format exec recommandé :**

```dockerfile
# CMD pour les arguments par défaut
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ENTRYPOINT + CMD pour plus de flexibilité
ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Références détaillées

Pour des exemples spécifiques par langage et framework :

- **[EXAMPLES.md](references/EXAMPLES.md)** - Templates complets par technologie (Python, Node.js, Go, Java, etc.)
- **[OPTIMIZATION.md](references/OPTIMIZATION.md)** - Techniques avancées d'optimisation
- **[SECURITY.md](references/SECURITY.md)** - Pratiques de sécurité détaillées

## Construction et tests

### Construire l'image

```bash
# Build basique
docker build -t mon-app:latest .

# Build avec pull de l'image de base
docker build --pull -t mon-app:latest .

# Build sans cache
docker build --no-cache -t mon-app:latest .

# Build avec arguments
docker build --build-arg VERSION=1.0 -t mon-app:latest .
```

### Tester l'image

```bash
# Vérifier la taille
docker images mon-app:latest

# Inspecter l'image
docker inspect mon-app:latest

# Analyser les layers
docker history mon-app:latest

# Tester le démarrage
docker run --rm -it mon-app:latest

# Scanner les vulnérabilités (avec Docker Scout)
docker scout cves mon-app:latest
```

## Maintenance continue

### Épingler avec digest (environnement critique)

```dockerfile
# Avec digest pour garantir la même image
FROM python:3.11-slim@sha256:abc123...
```

### Reconstruire régulièrement

```bash
# Forcer le pull de l'image de base et rebuild complet
docker build --pull --no-cache -t mon-app:latest .
```

### Automatiser avec CI/CD

Configurer votre pipeline pour :

- Builder l'image à chaque commit
- Tester l'image automatiquement
- Scanner les vulnérabilités
- Publier vers un registry
- Mettre à jour les digests automatiquement

## Scripts utilitaires

Deux scripts sont fournis pour faciliter l'analyse et la sécurité :

- **[analyze_image.sh](scripts/analyze_image.sh)** - Analyse complète d'une image (taille, layers, configuration, recommandations)
- **[scan_security.sh](scripts/scan_security.sh)** - Scan de sécurité avec Docker Scout, Trivy et Snyk

Usage :

```bash
# Analyser une image
./scripts/analyze_image.sh mon-app:latest

# Scanner la sécurité
./scripts/scan_security.sh mon-app:latest
```

## Commandes utiles

```bash
# Analyser l'utilisation d'espace
docker system df

# Nettoyer les ressources inutilisées
docker system prune -a

# Voir les layers d'une image
docker history --no-trunc mon-app:latest

# Exporter l'image
docker save mon-app:latest | gzip > mon-app.tar.gz

# Importer l'image
gunzip -c mon-app.tar.gz | docker load
```
