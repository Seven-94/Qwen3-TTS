# Quick Start UV

## Installation avec UV (recommandé)

UV est un gestionnaire d'environnement Python moderne et rapide.

### 1. Installer UV (si pas déjà fait)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Cloner et configurer

```bash
git clone <repo-url>
cd Qwen3-TTS
git checkout dev_perso_omo

# Copier la configuration
cp .env.example .env
# Éditer .env si nécessaire
```

### 3. Créer l'environnement et installer

```bash
# Créer l'environnement virtuel
uv venv

# Synchroniser les dépendances
uv sync

# Ou en une seule commande:
uv sync  # Crée automatiquement .venv si inexistant
```

### 4. Lancer l'application

```bash
# Méthode 1: Script de lancement
./start.sh

# Méthode 2: Manuellement
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Méthode 3: Avec rechargement automatique
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Vérifier le fonctionnement

- API Health: http://localhost:8000/health
- Interface Gradio: http://localhost:8000/ui
- Documentation API: http://localhost:8000/docs

## Commandes UV utiles

```bash
# Ajouter une dépendance
uv add <package>

# Supprimer une dépendance
uv remove <package>

# Mettre à jour les dépendances
uv sync --upgrade

# Lancer un script Python
uv run python script.py

# Activer l'environnement (optionnel)
source .venv/bin/activate
```

## Configuration UV

Le projet utilise `pyproject.toml` pour la configuration:
- **Dépendances**: Section `[project.dependencies]`
- **Python requis**: `requires-python = ">=3.9"`
- **Environnement**: Géré automatiquement par UV dans `.venv/`

## Résolution de problèmes

### Erreur: UV non trouvé
```bash
# Réinstaller UV
curl -LsSf https://astral.sh/uv/install.sh | sh
# Puis redémarrer le terminal
```

### Erreur: Dépendances CUDA
```bash
# PyTorch avec CUDA
uv add torch --index-url https://download.pytorch.org/whl/cu121
```

### Problème de synchronisation
```bash
# Forcer la resynchronisation
rm -rf .venv uv.lock
uv sync
```
