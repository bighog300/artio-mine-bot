#!/usr/bin/env bash
# =============================================================================
#  Artio Miner — redeploy script
#  Usage:  ./scripts/deploy.sh [OPTIONS]
#
#  Options:
#    --no-pull        Skip git pull (deploy current local code)
#    --no-migrate     Skip database migration after deploy
#    --build-only     Build images but don't start containers
#    --restart-only   Restart containers without rebuilding
#    --branch NAME    Pull a specific branch (default: current branch)
#    --help           Show this help message
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
step()    { echo -e "\n${BOLD}▶ $*${RESET}"; }
die()     { error "$*"; exit 1; }

# ── Defaults ──────────────────────────────────────────────────────────────────
DO_PULL=true
DO_MIGRATE=true
BUILD_ONLY=false
RESTART_ONLY=false
BRANCH=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-pull)      DO_PULL=false; shift ;;
    --no-migrate)   DO_MIGRATE=false; shift ;;
    --build-only)   BUILD_ONLY=true; shift ;;
    --restart-only) RESTART_ONLY=true; shift ;;
    --branch)       BRANCH="$2"; shift 2 ;;
    --help|-h)
      echo ""
      echo "  Artio Miner — redeploy"
      echo ""
      echo "  Usage: ./scripts/deploy.sh [OPTIONS]"
      echo ""
      echo "  Options:"
      echo "    --no-pull        Skip git pull"
      echo "    --no-migrate     Skip database migration"
      echo "    --build-only     Build images only, don't start"
      echo "    --restart-only   Restart without rebuilding"
      echo "    --branch NAME    Pull a specific git branch"
      echo "    --help           Show this message"
      echo ""
      exit 0 ;;
    *)
      die "Unknown option: $1. Run with --help for usage." ;;
  esac
done

# ── Preflight checks ──────────────────────────────────────────────────────────
step "Preflight checks"

# Must be run from the project root
cd "$PROJECT_DIR"

# Check required tools
for cmd in docker git; do
  command -v "$cmd" &>/dev/null || die "'$cmd' is not installed"
done

# Check docker-compose (v2 plugin or standalone)
if docker compose version &>/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
  COMPOSE="docker-compose"
else
  die "docker compose not found — install Docker Desktop or docker-compose"
fi

info "Docker Compose: $COMPOSE"
info "Project dir:    $PROJECT_DIR"

# Check .env exists
if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    warn ".env not found — copying from .env.example"
    cp .env.example .env
    warn "Edit .env and set OPENAI_API_KEY before running again"
    exit 1
  else
    die ".env file not found"
  fi
fi

success "Preflight OK"

# ── Git pull ──────────────────────────────────────────────────────────────────
if [[ "$DO_PULL" == true ]] && [[ "$RESTART_ONLY" == false ]]; then
  step "Pulling latest code from GitHub"

  # Check if we're in a git repo
  git rev-parse --git-dir &>/dev/null || die "Not a git repository"

  # Stash any local changes to tracked files
  if ! git diff --quiet HEAD 2>/dev/null; then
    warn "Local changes detected — stashing before pull"
    git stash push -m "deploy-auto-stash-$(date +%Y%m%d-%H%M%S)"
    STASHED=true
  else
    STASHED=false
  fi

  # Switch branch if requested
  if [[ -n "$BRANCH" ]]; then
    info "Switching to branch: $BRANCH"
    git fetch origin "$BRANCH"
    git checkout "$BRANCH"
  fi

  BEFORE=$(git rev-parse HEAD)
  git pull origin "$(git rev-parse --abbrev-ref HEAD)"
  AFTER=$(git rev-parse HEAD)

  if [[ "$BEFORE" == "$AFTER" ]]; then
    info "Already up to date ($(git rev-parse --short HEAD))"
  else
    success "Updated: $(git rev-parse --short "$BEFORE") → $(git rev-parse --short "$AFTER")"
    git log --oneline "$BEFORE".."$AFTER" | sed 's/^/    /'
  fi

  # Restore stash if we stashed
  if [[ "$STASHED" == true ]]; then
    info "Restoring stashed local changes"
    git stash pop || warn "Could not restore stash — check 'git stash list'"
  fi
else
  [[ "$RESTART_ONLY" == true ]] && info "Skipping pull (restart-only mode)"
  [[ "$DO_PULL" == false ]]     && info "Skipping pull (--no-pull)"
fi

# ── Show what we're deploying ─────────────────────────────────────────────────
step "Deploying"
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BRANCH_NOW=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
info "Branch: $BRANCH_NOW  |  Commit: $COMMIT"

# ── Build images ──────────────────────────────────────────────────────────────
if [[ "$RESTART_ONLY" == false ]]; then
  step "Building Docker images"
  SHA_TAG=$(git rev-parse --short HEAD)
  IMAGE_TAG="ghcr.io/bighog300/artio-mine-bot:api-$SHA_TAG"
  $COMPOSE build --no-cache --parallel
  docker tag artio-miner-api:latest $IMAGE_TAG
  step "Pushing to GHCR"
  echo $GITHUB_TOKEN | docker login ghcr.io -u bighog300 --password-stdin
  docker push $IMAGE_TAG
  # Update docker-compose.yml to use the tagged image
  sed -i "s|build: .|image: $IMAGE_TAG|" docker-compose.yml
  success "Images built, tagged, pushed, and compose updated: $IMAGE_TAG"
else
  info "Skipping build (--restart-only)"
fi

# ── Start containers ──────────────────────────────────────────────────────────
if [[ "$BUILD_ONLY" == false ]]; then
  step "Starting containers"
  $COMPOSE pull || info "Pull failed, using local images"
  $COMPOSE up -d
  success "Containers started"

  # Wait for API to be healthy
  step "Waiting for API to be ready"
  MAX_WAIT=60
  WAITED=0
  until curl -sf http://localhost:8765/health &>/dev/null; do
    if [[ $WAITED -ge $MAX_WAIT ]]; then
      error "API did not become healthy after ${MAX_WAIT}s"
      echo ""
      echo "Container logs:"
      $COMPOSE logs api --tail=30
      exit 1
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
  done
  echo ""
  success "API is healthy"
fi

# ── Run migrations ────────────────────────────────────────────────────────────
if [[ "$DO_MIGRATE" == true ]] && [[ "$BUILD_ONLY" == false ]]; then
  step "Running database migrations"
  $COMPOSE run --rm migrate
  success "Migrations applied"
else
  info "Skipping migrations"
fi

# ── Final summary ─────────────────────────────────────────────────────────────
if [[ "$BUILD_ONLY" == false ]]; then
  echo ""
  echo -e "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
  echo -e "${GREEN}${BOLD}  Artio Miner deployed successfully ✓   ${RESET}"
  echo -e "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
  echo ""
  echo -e "  ${BOLD}Admin UI${RESET}   →  http://localhost:5173"
  echo -e "  ${BOLD}API${RESET}        →  http://localhost:8765"
  echo -e "  ${BOLD}Health${RESET}     →  http://localhost:8765/health"
  echo -e "  ${BOLD}Commit${RESET}     →  $COMMIT  ($BRANCH_NOW)"
  echo ""
  echo -e "  Logs:   ${BLUE}$COMPOSE logs -f${RESET}"
  echo -e "  Inspect: ${BLUE}docker inspect $($COMPOSE ps -q api)${RESET}"
  echo -e "  Stop:   ${BLUE}$COMPOSE down${RESET}"
  echo ""
else
  echo ""
  success "Images built. Run '${COMPOSE} up -d' to start."
  echo ""
fi
