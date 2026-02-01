#!/bin/bash
#
# Script pour scanner la sécurité d'une image Docker
# Usage: ./scan_security.sh <image-name:tag>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <image-name:tag>"
    echo "Example: $0 myapp:latest"
    exit 1
fi

IMAGE=$1

echo "============================================"
echo "Scan de sécurité: $IMAGE"
echo "============================================"
echo ""

# Vérifier que l'image existe
if ! docker inspect "$IMAGE" > /dev/null 2>&1; then
    echo "❌ Erreur: L'image '$IMAGE' n'existe pas localement"
    exit 1
fi

# Vérifier quels outils sont disponibles
HAS_SCOUT=false
HAS_TRIVY=false
HAS_SNYK=false

if command -v docker scout &> /dev/null; then
    HAS_SCOUT=true
fi

if command -v trivy &> /dev/null; then
    HAS_TRIVY=true
fi

if command -v snyk &> /dev/null; then
    HAS_SNYK=true
fi

echo "🔍 Outils de scan disponibles"
echo "----------------------------------------"
echo "Docker Scout: $([ "$HAS_SCOUT" = true ] && echo "✅" || echo "❌ (installer avec Docker Desktop)")"
echo "Trivy: $([ "$HAS_TRIVY" = true ] && echo "✅" || echo "❌ (brew install aquasecurity/trivy/trivy)")"
echo "Snyk: $([ "$HAS_SNYK" = true ] && echo "✅" || echo "❌ (npm install -g snyk)")"
echo ""

if [ "$HAS_SCOUT" = false ] && [ "$HAS_TRIVY" = false ] && [ "$HAS_SNYK" = false ]; then
    echo "❌ Aucun outil de scan disponible"
    echo ""
    echo "Installez au moins un outil:"
    echo "  - Docker Scout: Inclus dans Docker Desktop"
    echo "  - Trivy: brew install aquasecurity/trivy/trivy"
    echo "  - Snyk: npm install -g snyk"
    exit 1
fi

# Scan avec Docker Scout
if [ "$HAS_SCOUT" = true ]; then
    echo "🛡️  Scan avec Docker Scout"
    echo "----------------------------------------"
    docker scout cves "$IMAGE" || echo "⚠️  Erreur lors du scan Docker Scout"
    echo ""
    
    echo "📊 Recommandations Docker Scout"
    echo "----------------------------------------"
    docker scout recommendations "$IMAGE" || echo "⚠️  Pas de recommandations disponibles"
    echo ""
fi

# Scan avec Trivy
if [ "$HAS_TRIVY" = true ]; then
    echo "🔬 Scan avec Trivy (HIGH et CRITICAL)"
    echo "----------------------------------------"
    trivy image --severity HIGH,CRITICAL "$IMAGE"
    echo ""
    
    echo "📋 Résumé complet Trivy"
    echo "----------------------------------------"
    trivy image --severity LOW,MEDIUM,HIGH,CRITICAL --format table "$IMAGE"
    echo ""
fi

# Scan avec Snyk
if [ "$HAS_SNYK" = true ]; then
    echo "🔐 Scan avec Snyk"
    echo "----------------------------------------"
    snyk container test "$IMAGE" || echo "⚠️  Vulnérabilités détectées (voir ci-dessus)"
    echo ""
fi

# Vérifications de base
echo "🔍 Vérifications de configuration"
echo "----------------------------------------"

# Utilisateur
USER=$(docker inspect --format='{{.Config.User}}' "$IMAGE")
if [ -z "$USER" ] || [ "$USER" = "root" ] || [ "$USER" = "0" ]; then
    echo "❌ Image s'exécute en tant que root"
else
    echo "✅ Utilisateur non-root: $USER"
fi

# Image de base
BASE_IMAGE=$(docker history "$IMAGE" --format "{{.CreatedBy}}" | grep "FROM" | head -n 1 | awk '{print $2}')
if [ -n "$BASE_IMAGE" ]; then
    echo "📦 Image de base: $BASE_IMAGE"
fi

# Taille
SIZE_MB=$(docker inspect --format='{{.Size}}' "$IMAGE" | awk '{print int($1/1024/1024)}')
echo "💾 Taille: ${SIZE_MB} MB"

echo ""
echo "📋 Checklist de sécurité"
echo "----------------------------------------"

# Checklist items
CHECKLIST=(
    "Utilisateur non-root configuré"
    "Image de base officielle utilisée"
    "Version de l'image épinglée (pas latest)"
    "Aucune vulnérabilité CRITICAL"
    "Packages minimaux installés"
    "Healthcheck configuré"
    "Ports minimaux exposés"
)

for item in "${CHECKLIST[@]}"; do
    echo "[ ] $item"
done

echo ""
echo "💡 Recommandations"
echo "----------------------------------------"
echo "1. Reconstruisez régulièrement vos images (au moins mensuellement)"
echo "2. Utilisez --pull lors du build pour obtenir les dernières mises à jour"
echo "3. Épinglez les versions avec digest pour les environnements critiques"
echo "4. Automatisez le scan dans votre CI/CD"
echo "5. Consultez les CVE détectées et évaluez leur impact"
echo ""

echo "============================================"
echo "Scan terminé ✅"
echo "============================================"
