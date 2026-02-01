# Optimisation avancée des images Docker

Ce document détaille les techniques avancées pour optimiser la taille et les performances de vos images Docker.

## Table des matières

- [Réduction de la taille des images](#réduction-de-la-taille-des-images)
- [Optimisation du cache de build](#optimisation-du-cache-de-build)
- [Build multi-architecture](#build-multi-architecture)
- [Techniques avancées de multi-stage](#techniques-avancées-de-multi-stage)
- [BuildKit avancé](#buildkit-avancé)
- [Analyse et debugging](#analyse-et-debugging)

---

## Réduction de la taille des images

### 1. Choisir la bonne image de base

**Impact de la taille de l'image de base :**

```dockerfile
# ❌ Grande image (>1GB)
FROM ubuntu:22.04

# ✅ Image slim (~150MB)
FROM python:3.11-slim

# ✅ Alpine (la plus petite, ~50MB)
FROM python:3.11-alpine
```

**Comparaison des tailles :**

- `ubuntu:22.04` → ~77 MB
- `python:3.11` → ~1 GB
- `python:3.11-slim` → ~130 MB
- `python:3.11-alpine` → ~50 MB
- `alpine:3.19` → ~7 MB
- `scratch` → 0 MB (pour binaires statiques)

### 2. Utiliser scratch pour les binaires statiques (Go, Rust)

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /build
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-w -s" -o app

# Image finale ultra-légère
FROM scratch
COPY --from=builder /build/app /app
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
ENTRYPOINT ["/app"]
```

**Note :** `scratch` ne contient rien du tout. Ajoutez manuellement ce dont vous avez besoin (certificats CA, fichiers de config, etc.).

### 3. Nettoyer agressivement dans chaque RUN

```dockerfile
# ❌ MAUVAIS : Chaque layer garde les données
RUN apt-get update
RUN apt-get install -y package
RUN apt-get clean

# ✅ BON : Tout dans un seul RUN
RUN apt-get update && \
    apt-get install -y --no-install-recommends package && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

### 4. Utiliser --no-install-recommends (Debian/Ubuntu)

```dockerfile
# ❌ Installe les packages recommandés (souvent inutiles)
RUN apt-get install -y python3

# ✅ N'installe que les dépendances requises
RUN apt-get install -y --no-install-recommends python3
```

### 5. Nettoyer les caches de package managers

```dockerfile
# Python
RUN pip install --no-cache-dir package

# Node.js
RUN npm ci --only=production && npm cache clean --force

# Debian/Ubuntu
RUN apt-get update && apt-get install -y package && \
    rm -rf /var/lib/apt/lists/*

# Alpine
RUN apk add --no-cache package

# Rust
RUN cargo build --release && \
    rm -rf target/release/deps target/release/build
```

### 6. Optimiser les flags de compilation (Go, Rust)

**Go : Réduire la taille du binaire**

```dockerfile
# Strips debug info et symbol table
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-w -s" \
    -a -installsuffix cgo \
    -o app

# -w : Omit DWARF symbol table
# -s : Omit symbol table and debug info
```

**Rust : Build optimisé pour la taille**

```dockerfile
# Dans Cargo.toml
[profile.release]
opt-level = 'z'     # Optimize for size
lto = true          # Enable Link Time Optimization
codegen-units = 1   # Reduce parallel code generation
strip = true        # Strip symbols
```

### 7. Utiliser UPX pour compresser les binaires

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /build

# Installer UPX
RUN apk add --no-cache upx

COPY . .
RUN go build -ldflags="-w -s" -o app

# Compresser le binaire
RUN upx --best --lzma app

FROM scratch
COPY --from=builder /build/app /app
ENTRYPOINT ["/app"]
```

**Attention :** UPX augmente le temps de démarrage (décompression). À utiliser seulement si la taille est critique.

### 8. Squash les layers (Docker BuildKit)

```bash
# Squash toutes les layers en une seule
docker build --squash -t myapp:latest .
```

**Attention :** Perd les bénéfices du cache de layers. À utiliser pour l'image finale de production uniquement.

---

## Optimisation du cache de build

### 1. Ordre optimal des instructions

**Principe :** Mettre les instructions qui changent rarement en premier.

```dockerfile
# ✅ Ordre optimal
FROM python:3.11-slim

# 1. Variables d'environnement (changent rarement)
ENV PYTHONUNBUFFERED=1

# 2. Installation des packages système (changent rarement)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential

# 3. Copie des fichiers de dépendances (changent parfois)
COPY requirements.txt .

# 4. Installation des dépendances (changent parfois)
RUN pip install -r requirements.txt

# 5. Copie du code source (change souvent)
COPY . .

# 6. Commande de démarrage (change rarement)
CMD ["python", "app.py"]
```

### 2. Utiliser des wildcards judicieusement

```dockerfile
# ❌ Invalide le cache si n'importe quel fichier change
COPY . /app

# ✅ Copie uniquement ce qui est nécessaire
COPY package*.json ./
RUN npm ci
COPY src/ ./src/
```

### 3. Cache mounts avec BuildKit

**Cacher le cache de pip (Python) :**

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Utiliser le cache mount pour pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

**Cacher node_modules (Node.js) :**

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine

RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline
```

**Cacher les packages Go :**

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.21

COPY go.mod go.sum ./

RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
```

### 4. Secret mounts (éviter de leak des secrets)

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Utiliser un secret mount au lieu d'ARG
RUN --mount=type=secret,id=pip_config \
    pip config set global.index-url $(cat /run/secrets/pip_config)
```

**Build avec le secret :**

```bash
docker build --secret id=pip_config,src=./pip.conf -t myapp .
```

### 5. Bind mounts (fichiers temporaires)

```dockerfile
# Au lieu de copier des fichiers temporaires
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip install -r /tmp/requirements.txt

# Les fichiers ne sont pas copiés dans l'image finale
```

---

## Build multi-architecture

### 1. Build pour plusieurs plateformes

```bash
# Créer un builder multi-plateforme
docker buildx create --name multiarch --use

# Build pour plusieurs architectures
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -t myapp:latest \
  --push \
  .
```

### 2. Dockerfile avec support multi-architecture

```dockerfile
# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM golang:1.21 AS builder

ARG TARGETOS
ARG TARGETARCH

WORKDIR /build
COPY . .

RUN GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -o app

FROM alpine:3.19
COPY --from=builder /build/app /app
ENTRYPOINT ["/app"]
```

---

## Techniques avancées de multi-stage

### 1. Stages réutilisables

```dockerfile
# syntax=docker/dockerfile:1

# Stage commun pour les dépendances système
FROM ubuntu:22.04 AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Stage pour le build
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY . /build
WORKDIR /build
RUN make build

# Stage pour les tests
FROM base AS test
COPY --from=builder /build/app /app
RUN /app --test

# Stage de production
FROM base AS production
COPY --from=builder /build/app /app
CMD ["/app"]
```

### 2. Build conditionnel avec TARGETSTAGE

```bash
# Build seulement jusqu'au stage de test
docker build --target test -t myapp:test .

# Build complet (production)
docker build --target production -t myapp:prod .
```

### 3. Copier depuis des stages externes

```dockerfile
FROM nginx:alpine AS production

# Copier depuis une autre image
COPY --from=node:20-alpine /usr/local/bin/node /usr/local/bin/node

# Copier les artefacts de build
COPY --from=builder /build/dist /usr/share/nginx/html
```

---

## BuildKit avancé

### 1. Activer BuildKit

```bash
# Variable d'environnement
export DOCKER_BUILDKIT=1
docker build .

# Ou utiliser buildx directement
docker buildx build .
```

### 2. Syntaxe BuildKit dans le Dockerfile

```dockerfile
# syntax=docker/dockerfile:1
# OU version spécifique
# syntax=docker/dockerfile:1.5

FROM python:3.11-slim
# ... reste du Dockerfile
```

### 3. Heredocs pour scripts complexes

```dockerfile
RUN <<EOF
apt-get update
apt-get install -y package1
apt-get install -y package2
rm -rf /var/lib/apt/lists/*
EOF
```

### 4. Copier avec patterns avancés

```dockerfile
# Exclure des fichiers lors de la copie
COPY --exclude=*.test.js src/ /app/src/

# Copier depuis un lien (avec checksum)
ADD --checksum=sha256:abc123... https://example.com/file.tar.gz /tmp/
```

### 5. Parallel stages

```dockerfile
# BuildKit build ces stages en parallèle automatiquement
FROM base AS builder1
RUN build-app1

FROM base AS builder2
RUN build-app2

FROM base AS final
COPY --from=builder1 /app1 /app1
COPY --from=builder2 /app2 /app2
```

---

## Analyse et debugging

### 1. Analyser la taille de l'image

```bash
# Voir la taille totale
docker images myapp:latest

# Voir la taille de chaque layer
docker history myapp:latest

# Avec plus de détails
docker history --no-trunc --human myapp:latest
```

### 2. Analyser les layers avec dive

```bash
# Installer dive
brew install dive

# Analyser une image
dive myapp:latest
```

**dive** affiche :

- La taille de chaque layer
- Les fichiers ajoutés/modifiés
- L'efficacité du cache
- Les suggestions d'optimisation

### 3. Scanner les vulnérabilités

```bash
# Avec Docker Scout
docker scout cves myapp:latest

# Avec Trivy
trivy image myapp:latest

# Avec Snyk
snyk container test myapp:latest
```

### 4. Benchmark des builds

```bash
# Mesurer le temps de build
time docker build -t myapp:latest .

# Build sans cache pour mesurer le pire cas
time docker build --no-cache -t myapp:latest .
```

### 5. Inspecter l'image

```bash
# Informations détaillées
docker inspect myapp:latest

# Extraire des informations spécifiques
docker inspect --format='{{.Size}}' myapp:latest
docker inspect --format='{{.Config.Env}}' myapp:latest
```

### 6. Entrer dans l'image pour déboguer

```bash
# Démarrer un shell interactif
docker run --rm -it myapp:latest sh

# Ou utiliser l'entrypoint par défaut (pas CMD)
docker run --rm -it --entrypoint sh myapp:latest

# Vérifier l'utilisateur
docker run --rm myapp:latest whoami

# Vérifier les variables d'environnement
docker run --rm myapp:latest env
```

---

## Checklist d'optimisation

- [ ] Utiliser une image de base minimale (slim/alpine)
- [ ] Implémenter un multi-stage build
- [ ] Ordonner les layers pour maximiser le cache
- [ ] Nettoyer les caches de package managers
- [ ] Utiliser --no-install-recommends pour apt-get
- [ ] Combiner les commandes RUN avec &&
- [ ] Utiliser .dockerignore pour exclure les fichiers inutiles
- [ ] Trier les arguments multi-lignes alphabétiquement
- [ ] Utiliser des cache mounts (BuildKit)
- [ ] Strips des binaires (Go, Rust)
- [ ] Éviter d'ajouter des fichiers temporaires dans les layers
- [ ] Analyser la taille avec docker history
- [ ] Scanner les vulnérabilités
- [ ] Utiliser des tags spécifiques (pas latest)
- [ ] Considérer scratch pour binaires statiques

---

## Exemples de gains de taille

### Python avec multi-stage optimisé

```dockerfile
# AVANT : Image simple (1.2 GB)
FROM python:3.11
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "app.py"]

# APRÈS : Multi-stage optimisé (150 MB)
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*
COPY . .
CMD ["python", "app.py"]

# Gain : 1.05 GB (~87%)
```

### Go avec scratch

```dockerfile
# AVANT : Image avec golang (1 GB)
FROM golang:1.21
COPY . /app
WORKDIR /app
RUN go build -o server
CMD ["./server"]

# APRÈS : Multi-stage avec scratch (10 MB)
FROM golang:1.21-alpine AS builder
WORKDIR /build
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-w -s" -o server

FROM scratch
COPY --from=builder /build/server /server
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
ENTRYPOINT ["/server"]

# Gain : 990 MB (~99%)
```
