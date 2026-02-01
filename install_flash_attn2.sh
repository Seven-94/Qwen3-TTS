#!/bin/bash

################################################################################
# Script d'installation automatique de Flash Attention avec PyTorch CUDA 13.0
# Compatible avec UV (gestionnaire d'environnement virtuel)
################################################################################

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction d'affichage
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

################################################################################
# Configuration
################################################################################
CUDA_VERSION="13.0"
PYTORCH_VERSION="2.10.0"
PYTORCH_INDEX_URL="https://download.pytorch.org/whl/cu130"

################################################################################
# Vérifications préalables
################################################################################
log "Vérification de l'installation de UV..."
if ! command -v uv &> /dev/null; then
    error "UV n'est pas installé. Installez-le avec: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

log "Vérification de CUDA..."
if command -v nvcc &> /dev/null; then
    CUDA_INSTALLED=$(nvcc --version | grep -oP "release \K[0-9.]+")
    log "CUDA version détectée: $CUDA_INSTALLED"
    if [[ "$CUDA_INSTALLED" != "$CUDA_VERSION" ]]; then
        warn "La version CUDA détectée ($CUDA_INSTALLED) ne correspond pas à la version attendue ($CUDA_VERSION)"
        read -p "Voulez-vous continuer ? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    warn "nvcc non trouvé. Assurez-vous que CUDA $CUDA_VERSION est installé."
fi

################################################################################
# Vérification de l'environnement virtuel UV
################################################################################
log "Vérification de l'environnement virtuel UV..."

# Vérifier que l'environnement virtuel existe
if [ ! -d ".venv" ]; then
    error "Aucun environnement virtuel détecté dans .venv/

Veuillez d'abord créer un environnement virtuel avec UV :

    uv venv

Puis relancez ce script :

    bash install_flash_attn2.sh
"
fi

log "Environnement virtuel .venv/ détecté ✓"

################################################################################
# Installation de PyTorch avec CUDA 13.0
################################################################################
log "Installation de PyTorch ${PYTORCH_VERSION} avec CUDA ${CUDA_VERSION}..."

# Désinstaller d'abord les versions potentiellement incompatibles
log "Nettoyage des versions existantes de PyTorch..."
uv pip uninstall torch torchvision torchaudio 2>/dev/null || true

# Nettoyer les bibliothèques CUDA 12 conflictuelles
log "Suppression des bibliothèques CUDA 12 conflictuelles..."
uv pip uninstall nvidia-nccl-cu12 nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 \
    nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 \
    nvidia-cufft-cu12 nvidia-cufile-cu12 nvidia-curand-cu12 \
    nvidia-cusolver-cu12 nvidia-cusparse-cu12 nvidia-cusparselt-cu12 \
    nvidia-nvjitlink-cu12 nvidia-nvshmem-cu12 nvidia-nvtx-cu12 2>/dev/null || true

# Installer PyTorch, TorchVision et TorchAudio avec CUDA 13.0 en UNE SEULE commande
# pour éviter les conflits de dépendances
log "Installation de torch, torchvision et torchaudio..."
uv pip install torch==${PYTORCH_VERSION} torchvision torchaudio --index-url ${PYTORCH_INDEX_URL}

# Forcer la suppression des bibliothèques CUDA 12 qui ont pu être réinstallées
log "Nettoyage final des bibliothèques CUDA 12..."
uv pip uninstall nvidia-nccl-cu12 nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 \
    nvidia-cuda-nvrtc-cu12 nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 \
    nvidia-cufft-cu12 nvidia-cufile-cu12 nvidia-curand-cu12 \
    nvidia-cusolver-cu12 nvidia-cusparse-cu12 nvidia-cusparselt-cu12 \
    nvidia-nvjitlink-cu12 nvidia-nvshmem-cu12 nvidia-nvtx-cu12 2>/dev/null || true

# Installer manuellement NCCL 2.23+ pour CUDA 13 si nécessaire
log "Installation de nvidia-nccl-cu13>=2.23..."
uv pip install "nvidia-nccl-cu13>=2.23"

# Vérification de l'installation de PyTorch
log "Vérification de l'installation de PyTorch..."
.venv/bin/python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')" || error "Échec de la vérification de PyTorch"

################################################################################
# Installation des dépendances de build
################################################################################
log "Installation des dépendances de build..."
uv pip install wheel ninja packaging psutil

################################################################################
# Nettoyage du cache
################################################################################
log "Nettoyage du cache UV..."
uv cache clean

################################################################################
# Installation de Flash Attention
################################################################################
log "Installation de Flash Attention (cela peut prendre plusieurs minutes)..."
log "La compilation se fait sans isolation pour utiliser le PyTorch CUDA 13.0 installé..."

# Installation sans isolation de build pour utiliser notre PyTorch
uv pip install flash-attn --no-build-isolation --no-cache-dir

################################################################################
# Vérification finale
################################################################################
log "Vérification de l'installation de Flash Attention..."
.venv/bin/python -c "import flash_attn; print(f'Flash Attention version: {flash_attn.__version__}')" && \
    log "${GREEN}✓ Flash Attention installé avec succès !${NC}" || \
    error "Échec de la vérification de Flash Attention"

################################################################################
# Résumé
################################################################################
echo ""
log "═══════════════════════════════════════════════════════════"
log "Installation terminée avec succès !"
log "═══════════════════════════════════════════════════════════"
log "PyTorch: ${PYTORCH_VERSION} (CUDA ${CUDA_VERSION})"
log "Flash Attention: installé"
log "Environnement: .venv/"
log ""
log "Pour activer l'environnement:"
log "  source .venv/bin/activate"
log ""
log "Pour l'utiliser avec UV:"
log "  uv run python votre_script.py"
log "═══════════════════════════════════════════════════════════"