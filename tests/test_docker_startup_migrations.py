from pathlib import Path

import yaml


def test_api_start_script_runs_alembic_upgrade_head() -> None:
    start_script = Path('scripts/start.sh').read_text(encoding='utf-8')
    assert 'alembic upgrade head' in start_script


def test_compose_api_uses_start_script_and_workers_wait_for_api_health() -> None:
    compose = yaml.safe_load(Path('docker-compose.yml').read_text(encoding='utf-8'))
    services = compose['services']

    api_command = services['api']['command']
    assert api_command[:2] == ['./scripts/start.sh', 'uvicorn']

    worker_depends_on = services['worker-1']['depends_on']
    assert worker_depends_on['api']['condition'] == 'service_healthy'
