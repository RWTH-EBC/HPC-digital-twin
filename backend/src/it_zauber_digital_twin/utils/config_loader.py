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


def get_influx_db_name() -> str:
    """Resolve the InfluxDB database name for the active DEPLOYMENT_ENV.

    Data is separated per deployment env into its own database so the
    dashboard only shows variables of the current env. 'local' and 'ebc'
    are aliased to 'itc' (consistent with coordinator_loader.which_deployment_env).
    """
    env_name = os.getenv("DEPLOYMENT_ENV", "itc")
    if env_name in ["local", "ebc"]:
        env_name = "itc"
    if env_name not in ["itc", "zih"]:
        env_name = "itc"
    return f"influx_db_{env_name}"


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

    # Per-deployment-env database; overrides the static fallback in the
    # config file so itc/zih data live in separate InfluxDB databases.
    config["INFLUX_DB_NAME"] = get_influx_db_name()
    
    return config

if __name__ == "__main__":
    config = get_iot_config()
    print(json.dumps(config, indent=4))