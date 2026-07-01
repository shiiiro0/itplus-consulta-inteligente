#!/usr/bin/env bash
# Publica la rama standalone actual como main en un repositorio GitHub nuevo.
#
# Uso:
#   ./scripts/push-to-new-repo.sh https://github.com/TU_USUARIO/itplus-consulta-inteligente.git
#
# Requisitos:
#   - Repo destino ya creado en GitHub (vacío, sin README)
#   - git configurado con acceso al remoto

set -euo pipefail

NEW_REMOTE_URL="${1:-}"
BRANCH="$(git branch --show-current)"

if [[ -z "$NEW_REMOTE_URL" ]]; then
  echo "Uso: $0 <url-repo-github-nuevo>"
  echo "Ejemplo: $0 https://github.com/mi-org/itplus-consulta-inteligente.git"
  exit 1
fi

if [[ "$BRANCH" != "cursor/itplus-standalone-c0eb" ]]; then
  echo "Advertencia: no estás en cursor/itplus-standalone-c0eb (rama actual: $BRANCH)"
  read -r -p "¿Continuar igual? [y/N] " ans
  [[ "${ans:-}" == "y" ]] || exit 1
fi

echo "→ Remoto nuevo: $NEW_REMOTE_URL"
echo "→ Rama local:   $BRANCH → main (remoto)"

if git remote get-url origin &>/dev/null; then
  echo "→ Renombrando origin a old-origin (repo original)"
  git remote rename origin old-origin
fi

git remote add origin "$NEW_REMOTE_URL"
git push -u origin "${BRANCH}:main"

echo ""
echo "Listo. Repo publicado en: $NEW_REMOTE_URL"
echo "Clonar con: git clone $NEW_REMOTE_URL"
