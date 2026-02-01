#!/bin/bash
# Script de lancement Qwen3-TTS Unified avec UV

echo "=========================================="
echo "  Qwen3-TTS Unified Interface"
echo "=========================================="

# Vérifier que UV est installé
if ! command -v uv &> /dev/null; then
    echo "❌ UV n'est pas installé. Installez-le avec:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Vérifier l'environnement
if [ ! -d "modele_tts" ]; then
    echo "❌ Erreur: Répertoire modele_tts/ non trouvé"
    exit 1
fi

# Créer les répertoires si nécessaires
mkdir -p voices cache

# Initialiser l'environnement UV si nécessaire
if [ ! -d ".venv" ]; then
    echo "🔄 Création de l'environnement virtuel UV..."
    uv venv
fi

# Synchroniser les dépendances
echo "🔄 Synchronisation des dépendances UV..."
uv sync

echo ""
echo "📁 Configuration:"
echo "  - Environnement: .venv/ (UV)"
echo "  - Modèles: modele_tts/"
echo "  - Voix: voices/"
echo "  - Cache: cache/"
echo ""
echo "🌐 Endpoints:"
echo "  - API: http://localhost:8000"
echo "  - UI:  http://localhost:8000/ui"
echo "  - Health: http://localhost:8000/health"
echo ""
echo "🚀 Démarrage du serveur..."
echo ""

# Lancer le serveur avec UV
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
