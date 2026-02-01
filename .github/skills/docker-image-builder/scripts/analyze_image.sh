#!/bin/bash
#
# Script pour analyser la taille et l'efficacité d'une image Docker
# Usage: ./analyze_image.sh <image-name:tag>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <image-name:tag>"
    echo "Example: $0 myapp:latest"
    exit 1
fi

IMAGE=$1

echo "============================================"
echo "Analyse de l'image Docker: $IMAGE"
echo "============================================"
echo ""

# Vérifier que l'image existe
if ! docker inspect "$IMAGE" > /dev/null 2>&1; then
    echo "❌ Erreur: L'image '$IMAGE' n'existe pas localement"
    echo "Essayez: docker pull $IMAGE"
    exit 1
fi

echo "📊 Informations générales"
echo "----------------------------------------"
docker images "$IMAGE" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.ID}}"
echo ""

echo "📦 Taille des layers"
echo "----------------------------------------"
docker history "$IMAGE" --human --format "table {{.CreatedBy}}\t{{.Size}}" | head -n 20
echo ""

echo "🔍 Détails de l'image"
echo "----------------------------------------"
echo "Created: $(docker inspect --format='{{.Created}}' "$IMAGE")"
echo "Architecture: $(docker inspect --format='{{.Architecture}}' "$IMAGE")"
echo "OS: $(docker inspect --format='{{.Os}}' "$IMAGE")"
echo "User: $(docker inspect --format='{{.Config.User}}' "$IMAGE")"
echo "WorkingDir: $(docker inspect --format='{{.Config.WorkingDir}}' "$IMAGE")"
echo ""

echo "🌐 Ports exposés"
echo "----------------------------------------"
PORTS=$(docker inspect --format='{{range $key, $value := .Config.ExposedPorts}}{{$key}} {{end}}' "$IMAGE")
if [ -z "$PORTS" ]; then
    echo "Aucun port exposé"
else
    echo "$PORTS"
fi
echo ""

echo "📂 Volumes"
echo "----------------------------------------"
VOLUMES=$(docker inspect --format='{{range $key, $value := .Config.Volumes}}{{$key}} {{end}}' "$IMAGE")
if [ -z "$VOLUMES" ]; then
    echo "Aucun volume déclaré"
else
    echo "$VOLUMES"
fi
echo ""

echo "🔐 Recommandations de sécurité"
echo "----------------------------------------"

# Vérifier l'utilisateur
USER=$(docker inspect --format='{{.Config.User}}' "$IMAGE")
if [ -z "$USER" ] || [ "$USER" = "root" ] || [ "$USER" = "0" ]; then
    echo "⚠️  L'image s'exécute en tant que root (non recommandé)"
else
    echo "✅ L'image utilise un utilisateur non-root: $USER"
fi

# Vérifier les healthchecks
HEALTHCHECK=$(docker inspect --format='{{.Config.Healthcheck}}' "$IMAGE")
if [ "$HEALTHCHECK" = "<nil>" ]; then
    echo "⚠️  Aucun healthcheck configuré"
else
    echo "✅ Healthcheck configuré"
fi

echo ""
echo "🧪 Suggestions d'optimisation"
echo "----------------------------------------"

# Analyser la taille totale
SIZE_MB=$(docker inspect --format='{{.Size}}' "$IMAGE" | awk '{print int($1/1024/1024)}')
if [ "$SIZE_MB" -gt 1000 ]; then
    echo "⚠️  Image très volumineuse ($SIZE_MB MB)"
    echo "   Considérez:"
    echo "   - Utiliser une image de base plus légère (alpine, slim)"
    echo "   - Implémenter un multi-stage build"
    echo "   - Nettoyer les caches de package managers"
elif [ "$SIZE_MB" -gt 500 ]; then
    echo "⚠️  Image assez volumineuse ($SIZE_MB MB)"
    echo "   Optimisations possibles disponibles"
else
    echo "✅ Taille raisonnable ($SIZE_MB MB)"
fi

# Compter les layers
LAYER_COUNT=$(docker history "$IMAGE" --quiet | wc -l)
if [ "$LAYER_COUNT" -gt 20 ]; then
    echo "⚠️  Nombre élevé de layers ($LAYER_COUNT)"
    echo "   Considérez combiner des commandes RUN avec &&"
else
    echo "✅ Nombre de layers acceptable ($LAYER_COUNT)"
fi

echo ""
echo "🔬 Commandes additionnelles utiles"
echo "----------------------------------------"
echo "Scanner les vulnérabilités:"
echo "  docker scout cves $IMAGE"
echo "  trivy image $IMAGE"
echo ""
echo "Analyser en détail avec dive:"
echo "  dive $IMAGE"
echo ""
echo "Démarrer un shell interactif:"
echo "  docker run --rm -it $IMAGE sh"
echo ""
echo "Exporter l'image:"
echo "  docker save $IMAGE | gzip > image.tar.gz"
echo ""

echo "============================================"
echo "Analyse terminée ✅"
echo "============================================"
