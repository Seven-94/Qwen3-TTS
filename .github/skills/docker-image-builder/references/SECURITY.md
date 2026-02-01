# Sécurité des images Docker

Ce document détaille les meilleures pratiques de sécurité pour construire des images Docker sécurisées.

## Table des matières

- [Principes fondamentaux](#principes-fondamentaux)
- [Utilisateurs non-root](#utilisateurs-non-root)
- [Gestion des secrets](#gestion-des-secrets)
- [Images de base sécurisées](#images-de-base-sécurisées)
- [Scan de vulnérabilités](#scan-de-vulnérabilités)
- [Réseau et ports](#réseau-et-ports)
- [Systèmes de fichiers](#systèmes-de-fichiers)
- [Build sécurisé](#build-sécurisé)
- [Runtime security](#runtime-security)

---

## Principes fondamentaux

### 1. Principe du moindre privilège

**Ne JAMAIS exécuter en tant que root en production**

```dockerfile
# ❌ MAUVAIS : root par défaut
FROM ubuntu:22.04
COPY app /app
CMD ["/app"]

# ✅ BON : utilisateur non-root
FROM ubuntu:22.04
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
COPY --chown=appuser:appuser app /app
USER appuser
CMD ["/app"]
```

### 2. Minimiser la surface d'attaque

- Utiliser des images de base minimales (alpine, slim, distroless)
- N'installer que les packages strictement nécessaires
- Retirer les outils de développement en production
- Utiliser multi-stage builds pour séparer build et runtime

### 3. Immutabilité

- Ne pas modifier les fichiers à l'exécution
- Utiliser des volumes pour les données persistantes
- Considérer les images read-only (`--read-only`)

---

## Utilisateurs non-root

### 1. Créer un utilisateur dédié

**Linux (Debian/Ubuntu) :**

```dockerfile
# Créer un groupe et un utilisateur
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Avec UID/GID explicites (recommandé)
RUN groupadd -r -g 1001 appuser && \
    useradd --no-log-init -r -g appuser -u 1001 appuser
```

**Alpine :**

```dockerfile
# Alpine utilise addgroup/adduser
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -u 1001 -G appuser
```

**Pourquoi `--no-log-init` ?**

- Bug dans Go archive/tar avec les grands UID
- Évite de remplir `/var/log/faillog` avec des NULL bytes

### 2. Changer le propriétaire des fichiers

```dockerfile
# Copier et changer le propriétaire en une seule commande
COPY --chown=appuser:appuser app /app

# Ou changer après coup
COPY app /app
RUN chown -R appuser:appuser /app
```

### 3. Basculer vers l'utilisateur non-root

```dockerfile
# IMPORTANT : Faire après toutes les opérations root
USER appuser

# Plus de commandes root après cette ligne !
```

### 4. Permissions de fichiers

```dockerfile
# Définir les permissions correctes
RUN chmod 755 /app/script.sh && \
    chmod 644 /app/config.yaml

# Ou avec COPY --chmod (BuildKit)
COPY --chmod=755 --chown=appuser:appuser script.sh /app/
```

### 5. Exemple complet multi-stage

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim

# Créer l'utilisateur AVANT de copier les fichiers
RUN groupadd -r -g 1001 appuser && \
    useradd --no-log-init -r -g appuser -u 1001 appuser

WORKDIR /app

# Copier les dépendances
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copier l'application
COPY --chown=appuser:appuser . .

# Mettre à jour PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Basculer vers non-root
USER appuser

CMD ["python", "app.py"]
```

---

## Gestion des secrets

### 1. NE JAMAIS hardcoder les secrets

```dockerfile
# ❌ DANGER : Secret dans l'image
ENV DATABASE_PASSWORD=supersecret

# ❌ DANGER : Même supprimé dans un layer ultérieur
RUN echo "password=secret" > /config && \
    rm /config  # Le secret est toujours dans le layer !

# ✅ BON : Injecter au runtime
# docker run -e DATABASE_PASSWORD=secret myapp
```

### 2. Utiliser des secret mounts (BuildKit)

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Le secret n'est pas copié dans l'image
RUN --mount=type=secret,id=pip_token \
    pip config set global.extra-index-url \
    https://token:$(cat /run/secrets/pip_token)@pypi.example.com/simple
```

**Build avec le secret :**

```bash
docker build --secret id=pip_token,src=./token.txt -t myapp .
```

### 3. Utiliser des fichiers .env au runtime

```bash
# Ne pas COPY .env dans l'image !
# Injecter au runtime
docker run --env-file .env myapp
```

### 4. Multi-stage pour les secrets de build

```dockerfile
FROM node:20 AS builder

# Secret uniquement dans le stage de build
ARG NPM_TOKEN
RUN echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > ~/.npmrc && \
    npm ci && \
    rm ~/.npmrc

# Stage de production sans le secret
FROM node:20-alpine
COPY --from=builder /app/node_modules ./node_modules
COPY . .
# Le NPM_TOKEN n'est pas dans cette image
```

### 5. Utiliser des gestionnaires de secrets

```bash
# Avec Docker Swarm secrets
docker service create \
  --secret db_password \
  --name myapp \
  myapp:latest

# Dans le container, accessible à /run/secrets/db_password
```

---

## Images de base sécurisées

### 1. Utiliser des images officielles vérifiées

```dockerfile
# ✅ Image officielle Docker
FROM python:3.11-slim

# ✅ Verified Publisher
FROM postgres:15-alpine

# ❌ Éviter les images non vérifiées
FROM random-user/python:latest
```

### 2. Épingler les versions avec digest

```dockerfile
# ✅ Épingler avec un digest SHA256
FROM python:3.11-slim@sha256:a8560b36e8b8210634f77d9f7f9efd7ffa463e380b75e2e74aff4511df3ef88c

# Obtenir le digest d'une image
# docker pull python:3.11-slim
# docker inspect python:3.11-slim --format='{{.RepoDigests}}'
```

### 3. Utiliser distroless (Google)

**Distroless** = Images sans distribution Linux (pas de shell, pas de package manager)

```dockerfile
FROM golang:1.21 AS builder
WORKDIR /build
COPY . .
RUN go build -o app

# Image distroless (pas de shell !)
FROM gcr.io/distroless/static-debian12
COPY --from=builder /build/app /app
ENTRYPOINT ["/app"]
```

**Avantages :**

- Surface d'attaque minimale
- Pas d'outils pour un attaquant
- Très petite taille

**Inconvénients :**

- Pas de shell (difficile à déboguer)
- Uniquement pour binaires statiques

### 4. Scanner les images de base

```bash
# Scanner avant d'utiliser
docker scout cves python:3.11-slim
trivy image python:3.11-alpine
```

---

## Scan de vulnérabilités

### 1. Intégrer le scan dans le workflow

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Installer et nettoyer en une seule commande
RUN apt-get update && \
    apt-get install -y --no-install-recommends package && \
    rm -rf /var/lib/apt/lists/*

# ... reste du Dockerfile
```

### 2. Scanner avec Docker Scout

```bash
# Analyser une image locale
docker scout cves myapp:latest

# Voir les recommandations
docker scout recommendations myapp:latest

# Comparer avec l'image de base
docker scout compare myapp:latest --to python:3.11-slim
```

### 3. Scanner avec Trivy

```bash
# Installation
brew install aquasecurity/trivy/trivy

# Scanner une image
trivy image myapp:latest

# Seulement les vulnérabilités HIGH et CRITICAL
trivy image --severity HIGH,CRITICAL myapp:latest

# Exporter en JSON
trivy image -f json -o results.json myapp:latest

# Fail si des vulnérabilités sont trouvées
trivy image --exit-code 1 --severity CRITICAL myapp:latest
```

### 4. Scanner avec Snyk

```bash
# Installation
npm install -g snyk

# Authentification
snyk auth

# Scanner une image
snyk container test myapp:latest

# Monitorer en continu
snyk container monitor myapp:latest
```

### 5. CI/CD - Exemple GitHub Actions

```yaml
name: Build and Scan

on: [push]

jobs:
  build-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Scan with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          severity: "HIGH,CRITICAL"
          exit-code: "1"

      - name: Scan with Docker Scout
        uses: docker/scout-action@v1
        with:
          command: cves
          image: myapp:${{ github.sha }}
```

---

## Réseau et ports

### 1. EXPOSE uniquement les ports nécessaires

```dockerfile
# ✅ Exposer seulement les ports utilisés
EXPOSE 8000/tcp

# ❌ Éviter d'exposer des ports de management/debug
# EXPOSE 9090/tcp  # Port de debugging
```

### 2. Ne pas binder à 0.0.0.0 si non nécessaire

```dockerfile
# Dans l'application, binder à localhost si possible
# app.run(host='127.0.0.1', port=8000)

# Si besoin d'accès externe
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Utiliser des réseaux Docker

```bash
# Créer un réseau isolé
docker network create --driver bridge app-network

# Lancer les containers dans ce réseau
docker run --network app-network --name db postgres:15
docker run --network app-network --name app myapp:latest
```

---

## Systèmes de fichiers

### 1. Utiliser des volumes pour les données sensibles

```dockerfile
# Déclarer un volume pour les données
VOLUME /var/lib/postgresql/data
VOLUME /app/uploads
```

```bash
# Monter un volume au runtime
docker run -v app-data:/app/data myapp:latest
```

### 2. Read-only filesystem

```bash
# Lancer le container en read-only
docker run --read-only --tmpfs /tmp myapp:latest
```

```dockerfile
# Préparer l'image pour read-only
# S'assurer que l'app n'écrit pas sur le filesystem
# Utiliser tmpfs pour les fichiers temporaires
```

### 3. Permissions strictes

```dockerfile
# Fichiers de configuration en lecture seule
COPY --chmod=444 config.yaml /app/config.yaml

# Scripts exécutables
COPY --chmod=555 entrypoint.sh /app/entrypoint.sh

# Répertoires
RUN mkdir -p /app/data && chmod 700 /app/data
```

---

## Build sécurisé

### 1. Utiliser .dockerignore

```
# Secrets et configs sensibles
.env
.env.*
secrets/
*.key
*.pem
*.p12
id_rsa*

# Fichiers sensibles
passwords.txt
credentials.json
.aws/
.ssh/

# Historique et logs
.bash_history
.history
*.log

# Code source (si build artifacts seulement)
src/
tests/
```

### 2. Multi-stage pour séparer build et runtime

```dockerfile
# Build avec outils complets
FROM ubuntu:22.04 AS builder
RUN apt-get update && apt-get install -y build-essential gcc make
COPY . /build
WORKDIR /build
RUN make

# Runtime minimal
FROM ubuntu:22.04
# Ne copie QUE le binaire, pas les outils de build
COPY --from=builder /build/app /app
CMD ["/app"]
```

### 3. Ne pas inclure les outils de debug en production

```dockerfile
# ❌ MAUVAIS
FROM python:3.11
RUN apt-get update && apt-get install -y \
    vim \
    gdb \
    strace \
    tcpdump

# ✅ BON : Build minimal
FROM python:3.11-slim
# Rien d'autre que le nécessaire
```

### 4. Vérifier les checksums

```dockerfile
# Vérifier l'intégrité des téléchargements
ADD --checksum=sha256:abc123... \
    https://example.com/file.tar.gz /tmp/file.tar.gz
```

---

## Runtime security

### 1. Limiter les capabilities

```bash
# Retirer toutes les capabilities
docker run --cap-drop=ALL myapp:latest

# Ajouter seulement celles nécessaires
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myapp:latest
```

### 2. Utiliser seccomp profiles

```bash
# Utiliser le profile seccomp par défaut (recommandé)
docker run --security-opt seccomp=default.json myapp:latest
```

### 3. AppArmor / SELinux

```bash
# Avec AppArmor (Ubuntu/Debian)
docker run --security-opt apparmor=docker-default myapp:latest

# Avec SELinux (RHEL/CentOS)
docker run --security-opt label=type:container_runtime_t myapp:latest
```

### 4. Ne pas utiliser --privileged

```bash
# ❌ DANGER : Accès complet à l'hôte
docker run --privileged myapp:latest

# ✅ BON : Permissions minimales
docker run myapp:latest
```

### 5. Limiter les ressources

```bash
# Limiter CPU et mémoire
docker run \
  --memory="512m" \
  --memory-swap="512m" \
  --cpus="1.0" \
  myapp:latest
```

---

## Checklist de sécurité

### Build time

- [ ] Image de base officielle et vérifiée
- [ ] Version de l'image épinglée (digest si critique)
- [ ] Multi-stage build pour séparer build/runtime
- [ ] Utilisateur non-root créé et utilisé
- [ ] .dockerignore complet (secrets exclus)
- [ ] Pas de secrets hardcodés dans les layers
- [ ] Packages minimaux installés
- [ ] Caches nettoyés après installation
- [ ] Permissions de fichiers strictes
- [ ] Scan de vulnérabilités intégré
- [ ] Labels informatifs ajoutés
- [ ] Healthcheck configuré

### Runtime

- [ ] Container lancé en non-root
- [ ] Capabilities minimales
- [ ] Réseau isolé
- [ ] Volumes pour données sensibles
- [ ] Secrets injectés au runtime (pas dans l'image)
- [ ] Read-only filesystem (si possible)
- [ ] Limits de ressources configurées
- [ ] Logs centralisés
- [ ] Monitoring actif
- [ ] Mises à jour régulières

---

## Outils de sécurité recommandés

### Scan d'images

- **Docker Scout** - Intégré à Docker Desktop
- **Trivy** - Scanner open source complet
- **Snyk** - Scanner commercial avec remediation
- **Grype** - Scanner de vulnérabilités Anchore

### Analyse statique

- **Hadolint** - Linter pour Dockerfiles
- **Dockle** - Vérification des best practices
- **Dive** - Analyse des layers

### Runtime security

- **Falco** - Détection d'anomalies runtime
- **Aqua Security** - Solution complète
- **Sysdig Secure** - Monitoring et sécurité

---

## Ressources supplémentaires

- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Snyk Docker Security](https://snyk.io/learn/docker-security/)
