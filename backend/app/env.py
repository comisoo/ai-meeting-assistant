from pathlib import Path

from dotenv import load_dotenv


def load_app_env() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    candidate_paths = [
        backend_dir / ".env",
        backend_dir.parent / ".env",
    ]

    for env_path in candidate_paths:
        if env_path.exists():
            load_dotenv(env_path)
