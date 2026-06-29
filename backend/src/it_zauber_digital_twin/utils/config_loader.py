import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_project_root() -> Path:
    """Finds the project root by looking for pyproject.toml"""
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not find project root (pyproject.toml not found)")


def get_iot_config() -> dict:
    project_root = get_project_root()
    config_dir = project_root / "configs"
    
    config_filename = "iot_config_local.json"
    config_path = config_dir / config_filename

    if not config_path.exists():
        # Fallback or error?
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with open(config_path, "r") as f:
        config = json.load(f)

    is_docker = os.getenv("IS_DOCKER", "false").lower() == "true"
    
    host = "host.docker.internal" if is_docker else "localhost"
    
    cb_port = config["CB_PORT"]
    iota_port = config["IOTA_PORT"]
    postgres_port = config["POSTGRES_PORT"]
    
    cb_url = f"http://{host}:{cb_port}"
    iota_url = f"http://{host}:{iota_port}"
    postgres_ip = f"{host}:{postgres_port}"
    
    config["CB_URL"] = cb_url
    config["IOTA_URL"] = iota_url
    config["POSTGRES_IP"] = postgres_ip
    config["HOST"] = host
    
    return config

if __name__ == "__main__":
    config = get_iot_config()
    print(json.dumps(config, indent=4))