from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_deploy_script_exists_and_exposes_main_commands() -> None:
    script = REPO_ROOT / "deploy.sh"

    assert script.exists(), "deploy.sh should exist at repository root"

    content = script.read_text(encoding="utf-8")
    assert "up)" in content
    assert "down)" in content
    assert "restart)" in content
    assert "status)" in content
    assert "logs)" in content


def test_deploy_script_builds_and_starts_frontend_and_backend() -> None:
    content = (REPO_ROOT / "deploy.sh").read_text(encoding="utf-8")

    assert "python -m venv .venv" in content or "python3 -m venv .venv" in content
    assert (
        "python -m pip install -e ." in content or '"$(python_bin)" -m pip install -e .' in content
    )
    assert "npm -C frontend install" in content or "npm -C frontend ci" in content
    assert "npm -C frontend run build" in content
    assert "uvicorn app.api.http:app" in content
    assert "scripts/frontend_proxy_server.py" in content
    assert "8001" in content
    assert "4180" in content


def test_deploy_script_checks_health_and_writes_runtime_metadata() -> None:
    content = (REPO_ROOT / "deploy.sh").read_text(encoding="utf-8")

    assert "/api/health" in content
    assert "/api/auth/login" in content
    assert "curl --noproxy '*'" in content
    assert ".runtime" in content
    assert "backend.deploy.pid" in content
    assert "frontend.deploy.pid" in content
