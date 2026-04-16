# Documentation Layout

This repository was cleaned up so documentation is centralized under `docs/`.

## Structure

- `docs/root/` — former top-level markdown/text documentation files.
- `docs/legacy/` — legacy documentation bundles moved from top-level directories:
  - `backfill-docs-complete/`
  - `source_operations_spec/`
  - `operator_control_spec/`
  - `codex_job_visibility_docs/`
- `docs/backfill/`, `docs/audit/` — existing project documentation kept in place.

## Verification

### Document cleanup check

Run to confirm no stray root-level docs remain (except `README.md` and `AGENTS.md`):

```bash
find . -maxdepth 1 -type f | sed 's#^./##' | sort
```

### Dependency consistency check

Run to validate `requirements.txt` and `pyproject.toml` dependencies are in sync:

```bash
python - <<'PY'
from pathlib import Path
import tomli as toml
import re

pp=toml.loads(Path('pyproject.toml').read_text())
req=[x.strip() for x in Path('requirements.txt').read_text().splitlines() if x.strip() and not x.strip().startswith('#')]
norm=lambda s: re.match(r'([A-Za-z0-9_.-]+)',s).group(1).lower().replace('_','-')
req_names={norm(r) for r in req}
proj_names={norm(d) for d in pp.get('project',{}).get('dependencies',[])}

print('requirements_count',len(req_names))
print('pyproject_count',len(proj_names))
print('missing_in_pyproject', sorted(req_names-proj_names))
print('missing_in_requirements', sorted(proj_names-req_names))
PY
```
