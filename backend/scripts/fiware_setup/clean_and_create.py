import json
import os
from pathlib import Path

from it_zauber_digital_twin.utils.fiware_utils import (
    create_entities_and_devices,
    delete_all_entities_and_devices,
    get_all_entity_ids,
)
from it_zauber_digital_twin.utils.utils import setup_logger

LOGGER = setup_logger("fiware_setup")

# Where the last provisioned DEPLOYMENT_ENV is remembered across container
# restarts. Backed by a named docker volume (see docker-compose.yml).
MARKER_PATH = Path(
    os.getenv("FIWARE_STATE_FILE", "/opt/fiware_state/provisioned_env")
)


def resolve_deployment_env() -> str:
    """Resolve DEPLOYMENT_ENV to a concrete entity set ('itc' or 'zih').

    Mirrors the mapping in
    it_zauber_digital_twin.utils.coordinator_loader.which_deployment_env:
    'local' and 'ebc' are aliased to 'itc'.
    """
    env_name = os.getenv("DEPLOYMENT_ENV", "itc")
    if env_name not in ["local", "zih", "itc", "ebc"]:
        raise ValueError(
            f"Unknown DEPLOYMENT_ENV: {env_name}. "
            "Must be one of 'local', 'zih', 'itc', 'ebc'."
        )
    if env_name in ["local", "ebc"]:
        env_name = "itc"
    return env_name


def load_entities(env_name: str) -> list:
    entities_p = Path(__file__).parent / f"{env_name}_entities.json"
    with open(entities_p, "r") as f:
        return json.load(f)


def device_ids_from_entities(entities: list) -> list:
    return [i["id"].split(":")[-1] for i in entities]


def read_marker() -> str | None:
    try:
        return MARKER_PATH.read_text().strip() or None
    except FileNotFoundError:
        return None


def write_marker(env_name: str) -> None:
    MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKER_PATH.write_text(env_name)


def clean_and_create(entities: list) -> None:
    device_ids = device_ids_from_entities(entities)
    delete_all_entities_and_devices()
    create_entities_and_devices(
        entities=entities, device_ids=device_ids, block_size=1000
    )


def provision():
    env_name = resolve_deployment_env()
    last_env = read_marker()
    entities = load_entities(env_name)

    if last_env != env_name:
        LOGGER.info(
            "Deployment env changed (%s -> %s). Running clean and create.",
            last_env,
            env_name,
        )
        clean_and_create(entities)
        write_marker(env_name)
        return

    # Same env as last run: only verify that all entities still exist.
    target_ids = {ent["id"] for ent in entities}
    existing_ids = set(get_all_entity_ids())
    missing = target_ids - existing_ids

    if missing:
        LOGGER.info(
            "Deployment env unchanged (%s) but %d entity(ies) missing "
            "(e.g. %s). Running clean and create.",
            env_name,
            len(missing),
            next(iter(missing)),
        )
        clean_and_create(entities)
        write_marker(env_name)
    else:
        LOGGER.info(
            "Deployment env unchanged (%s) and all %d entities present. "
            "Nothing to do.",
            env_name,
            len(target_ids),
        )


if __name__ == "__main__":
    provision()
