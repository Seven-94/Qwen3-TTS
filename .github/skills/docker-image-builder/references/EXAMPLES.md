# Exemples de Dockerfiles par technologie

Ce document contient des templates Dockerfile optimisés pour différents langages et frameworks.

## Table des matières

- [Python](#python)
  - [Python Application Simple](#python-application-simple)
  - [FastAPI / Flask](#fastapi--flask)
  - [Django](#django)
- [Node.js](#nodejs)
  - [Node.js Application Simple](#nodejs-application-simple)
  - [Next.js](#nextjs)
  - [Express.js](#expressjs)
- [Go](#go)
- [Java](#java)
  - [Spring Boot](#spring-boot)
  - [Maven Application](#maven-application)
- [Rust](#rust)
- [Ruby](#ruby)
- [PHP](#php)

---

## Python

### Python Application Simple

```dockerfile
# syntax=docker/dockerfile:1

# Stage de build
FROM python:3.11-slim AS builder

WORKDIR /build

# Installer les dépendances système nécessaires pour la compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage de production
FROM python:3.11-slim

# Créer un utilisateur non-root
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

WORKDIR /app

# Copier les dépendances depuis le builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copier le code de l'application
COPY --chown=appuser:appuser . .

# Mettre à jour PATH pour inclure les binaires Python user
ENV PATH=/home/appuser/.local/bin:$PATH

# Basculer vers l'utilisateur non-root
USER appuser

# Port par défaut
EXPOSE 8000

# Commande de démarrage
CMD ["python", "app.py"]
```

### FastAPI / Flask

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

WORKDIR /build

# Installer les dépendances de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage de production
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="votre-email@example.com"
LABEL description="FastAPI Application"
LABEL version="1.0"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Créer un utilisateur non-root
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

WORKDIR /app

# Copier et installer les wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

# Copier le code de l'application
COPY --chown=appuser:appuser ./app ./app

# Basculer vers l'utilisateur non-root
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

EXPOSE 8000

# Utiliser uvicorn pour servir FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Django

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

WORKDIR /build

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage de production
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=myproject.settings

# Installer les dépendances runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN groupadd -r django && useradd --no-log-init -r -g django django

WORKDIR /app

# Copier et installer les wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

# Copier le projet Django
COPY --chown=django:django . .

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput

USER django

EXPOSE 8000

CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

---

## Node.js

### Node.js Application Simple

```dockerfile
# syntax=docker/dockerfile:1

FROM node:20-alpine AS builder

WORKDIR /build

# Copier les fichiers de dépendances
COPY package*.json ./

# Installer les dépendances (production + dev pour le build)
RUN npm ci

# Copier le code source
COPY . .

# Build de l'application (si nécessaire)
RUN npm run build

# Stage de production
FROM node:20-alpine

# Variables d'environnement
ENV NODE_ENV=production

# Créer un utilisateur non-root
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

WORKDIR /app

# Copier les fichiers de dépendances
COPY package*.json ./

# Installer uniquement les dépendances de production
RUN npm ci --only=production && npm cache clean --force

# Copier les artefacts de build
COPY --from=builder --chown=nodejs:nodejs /build/dist ./dist

USER nodejs

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

### Next.js

```dockerfile
# syntax=docker/dockerfile:1

FROM node:20-alpine AS deps

WORKDIR /app

# Installer les dépendances basées sur le lock file
COPY package.json package-lock.json ./
RUN npm ci

# Stage de build
FROM node:20-alpine AS builder

WORKDIR /app

# Copier les dépendances
COPY --from=deps /app/node_modules ./node_modules

# Copier le code source
COPY . .

# Désactiver la télémétrie pendant le build
ENV NEXT_TELEMETRY_DISABLED=1

# Build de Next.js
RUN npm run build

# Stage de production
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Créer un utilisateur non-root
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copier les fichiers nécessaires
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000

CMD ["node", "server.js"]
```

### Express.js

```dockerfile
# syntax=docker/dockerfile:1

FROM node:20-alpine AS builder

WORKDIR /build

COPY package*.json ./
RUN npm ci

COPY . .

# Transpiler TypeScript si nécessaire
RUN npm run build

# Stage de production
FROM node:20-alpine

ENV NODE_ENV=production

RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

COPY --from=builder --chown=nodejs:nodejs /build/dist ./dist

USER nodejs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

CMD ["node", "dist/server.js"]
```

---

## Go

```dockerfile
# syntax=docker/dockerfile:1

FROM golang:1.21-alpine AS builder

WORKDIR /build

# Installer les outils de build nécessaires
RUN apk add --no-cache git ca-certificates

# Copier les fichiers go.mod et go.sum
COPY go.mod go.sum ./

# Télécharger les dépendances
RUN go mod download

# Copier le code source
COPY . .

# Build de l'application (binaire statique)
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s" \
    -o /app/server \
    ./cmd/server

# Stage de production (scratch pour binaire statique)
FROM alpine:3.19

# Installer les certificats CA
RUN apk --no-cache add ca-certificates tzdata

# Créer un utilisateur non-root
RUN addgroup -g 1001 -S appuser && adduser -S appuser -u 1001 -G appuser

WORKDIR /app

# Copier le binaire depuis le builder
COPY --from=builder --chown=appuser:appuser /app/server ./server

USER appuser

EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

ENTRYPOINT ["./server"]
```

---

## Java

### Spring Boot

```dockerfile
# syntax=docker/dockerfile:1

FROM eclipse-temurin:21-jdk AS builder

WORKDIR /build

# Copier les fichiers Maven/Gradle
COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .

# Télécharger les dépendances (pour le cache)
RUN ./mvnw dependency:go-offline

# Copier le code source
COPY src ./src

# Build de l'application
RUN ./mvnw package -DskipTests

# Extract layered JAR
RUN java -Djarmode=layertools -jar target/*.jar extract

# Stage de production
FROM eclipse-temurin:21-jre-alpine

# Créer un utilisateur non-root
RUN addgroup -g 1001 -S spring && adduser -S spring -u 1001 -G spring

WORKDIR /app

# Copier les layers dans l'ordre (optimisation du cache)
COPY --from=builder --chown=spring:spring build/dependencies/ ./
COPY --from=builder --chown=spring:spring build/spring-boot-loader/ ./
COPY --from=builder --chown=spring:spring build/snapshot-dependencies/ ./
COPY --from=builder --chown=spring:spring build/application/ ./

USER spring

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
```

### Maven Application

```dockerfile
# syntax=docker/dockerfile:1

FROM maven:3.9-eclipse-temurin-21 AS builder

WORKDIR /build

# Copier pom.xml et télécharger les dépendances
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copier et compiler le code
COPY src ./src
RUN mvn package -DskipTests

# Stage de production
FROM eclipse-temurin:21-jre-alpine

RUN addgroup -g 1001 -S java && adduser -S java -u 1001 -G java

WORKDIR /app

# Copier le JAR
COPY --from=builder --chown=java:java /build/target/*.jar app.jar

USER java

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
```

---

## Rust

```dockerfile
# syntax=docker/dockerfile:1

FROM rust:1.75-slim AS builder

WORKDIR /build

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier Cargo.toml et Cargo.lock
COPY Cargo.toml Cargo.lock ./

# Créer un projet dummy pour cache les dépendances
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# Copier le vrai code source
COPY src ./src

# Build final
RUN cargo build --release

# Stage de production
FROM debian:bookworm-slim

# Installer les dépendances runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

WORKDIR /app

# Copier le binaire
COPY --from=builder --chown=appuser:appuser /build/target/release/myapp ./myapp

USER appuser

EXPOSE 8080

CMD ["./myapp"]
```

---

## Ruby

```dockerfile
# syntax=docker/dockerfile:1

FROM ruby:3.2-slim AS builder

WORKDIR /build

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier Gemfile
COPY Gemfile Gemfile.lock ./

# Installer les gems
RUN bundle config set --local deployment 'true' && \
    bundle config set --local without 'development test' && \
    bundle install

# Stage de production
FROM ruby:3.2-slim

ENV RAILS_ENV=production \
    RACK_ENV=production

# Installer les dépendances runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN groupadd -r rails && useradd --no-log-init -r -g rails rails

WORKDIR /app

# Copier les gems
COPY --from=builder --chown=rails:rails /usr/local/bundle /usr/local/bundle

# Copier l'application
COPY --chown=rails:rails . .

# Précompiler les assets
RUN bundle exec rake assets:precompile

USER rails

EXPOSE 3000

CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]
```

---

## PHP

```dockerfile
# syntax=docker/dockerfile:1

FROM php:8.2-fpm-alpine AS builder

WORKDIR /build

# Installer Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copier composer.json et composer.lock
COPY composer.json composer.lock ./

# Installer les dépendances PHP
RUN composer install --no-dev --no-scripts --no-autoloader --prefer-dist

# Copier le code source
COPY . .

# Générer l'autoloader optimisé
RUN composer dump-autoload --optimize --classmap-authoritative

# Stage de production
FROM php:8.2-fpm-alpine

# Installer les extensions PHP nécessaires
RUN apk add --no-cache \
    libpng-dev \
    libzip-dev \
    && docker-php-ext-install \
    gd \
    mysqli \
    pdo_mysql \
    zip

# Créer un utilisateur non-root
RUN addgroup -g 1001 -S www && adduser -S www -u 1001 -G www

WORKDIR /var/www/html

# Copier l'application
COPY --from=builder --chown=www:www /build .

USER www

EXPOSE 9000

CMD ["php-fpm"]
```

---

## Notes communes

### .dockerignore recommandé

```
# Version control
.git
.gitignore
.github

# Dependencies
node_modules
__pycache__
*.pyc
.venv
venv
vendor

# Build artifacts
dist
build
target
*.egg-info

# IDE
.vscode
.idea
*.swp
*.swo

# Documentation
*.md
docs/

# Tests
tests/
test/
*.test.js
*_test.go

# CI/CD
.gitlab-ci.yml
.travis.yml
Jenkinsfile
.circleci

# Secrets
.env
.env.*
secrets/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
```

### Health checks recommandés

Ajoutez toujours un endpoint de healthcheck dans votre application et configurez `HEALTHCHECK` :

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD <commande-de-test> || exit 1
```
