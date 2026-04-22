from pathlib import Path


def test_nginx_uses_docker_dns_for_api_upstream() -> None:
    nginx_conf = Path("frontend/nginx.conf").read_text(encoding="utf-8")
    assert "proxy_pass http://api:8000/api/;" in nginx_conf
    assert "proxy_pass http://api:8000/health;" in nginx_conf
    assert "172.18." not in nginx_conf


def test_frontend_image_does_not_use_runtime_api_url_rewrite_script() -> None:
    dockerfile = Path("Dockerfile.frontend").read_text(encoding="utf-8")
    assert "inject-api-url.sh" not in dockerfile
    assert "VITE_API_URL" not in dockerfile
    assert "npm run build" in dockerfile
