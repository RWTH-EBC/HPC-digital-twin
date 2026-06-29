import json
import time
from datetime import datetime, timezone
from pprint import pprint

import pandas as pd
import requests
from psycopg2 import OperationalError
from requests.adapters import HTTPAdapter
from requests.exceptions import JSONDecodeError
from sqlalchemy import create_engine, text
from tqdm import tqdm
from typing import Tuple
from urllib3.util.retry import Retry

from it_zauber_digital_twin.utils.utils import setup_logger
from it_zauber_digital_twin.utils import get_iot_config

config = get_iot_config()

POSTGRES_IP = config["POSTGRES_IP"]
CB_URL = config["CB_URL"]
POST_HEADERS = config["POST_HEADERS"]
POST_HEADERS_NO_LD = config["POST_HEADERS_NO_LD"]
IOTA_HEADERS = config["IOTA_HEADERS"]
IOTA_URL = config["IOTA_URL"]
APIKEY = config["APIKEY"]

CREATION_LOGGER = setup_logger("creation_logger")

# Shared HTTP session with automatic retry on connection errors and server errors.
# Retries up to 3 times with exponential backoff (0.5s, 1s, 2s) before raising.
_retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET", "POST", "DELETE"],
    raise_on_status=False,
)
_adapter = HTTPAdapter(max_retries=_retry)
session = requests.Session()
session.mount("http://", _adapter)
session.mount("https://", _adapter)


def get_sql_engine():
    # Scheme: "postgresql+psycopg2://<USERNAME>:<PASSWORD>@<IP_ADDRESS>:<PORT>/<DATABASE_NAME>"
    DATABASE_URI = f"postgresql+psycopg2://orion:orion@{POSTGRES_IP}/orion_test"
    try:
        engine = create_engine(DATABASE_URI)
    except OperationalError:
        dummy_create()
        time.sleep(0.1)
        engine = create_engine(DATABASE_URI)
    return engine


def dummy_create():
    entities = []

    dummy_entity = {
        "id": "urn:ngsi-ld:dummy_ent",
        "type": "dummy",
        "Test": {"type": "Property", "value": ""},
        "@context": ["http://context/ngsi-context.jsonld"],
    }

    entities.append(dummy_entity)

    resp = session.post(
        f"{CB_URL}/ngsi-ld/v1/entityOperations/upsert",
        headers=POST_HEADERS,
        json=entities,
    )

    if not resp.ok:
        pprint(resp.json())
        raise TypeError("Error when posting entitys")

    if resp.status_code == 207:
        pprint(resp.json())
        raise TypeError("Error when posting entities")
    time.sleep(0.1)


def get_sql_df():
    engine = get_sql_engine()
    with engine.begin() as conn:
        query = text('select * from "attributes"')
        df = pd.read_sql_query(query, con=conn)

    return df


def get_all_entity_ids():
    limit = 1000
    offset = 0

    r = session.get(
        f"{CB_URL}/ngsi-ld/v1/entities/?local=true&limit=10", headers=POST_HEADERS
    )

    if r.status_code == 404:
        dummy_create()
        time.sleep(0.1)

    all_ids = []
    while True:
        r = session.get(
            f"{CB_URL}/ngsi-ld/v1/entities/?local=true&limit={limit}&offset={offset}",
            headers=POST_HEADERS,
        )
        if not r.ok:
            pprint(r)
            pprint(r.json())
            raise TypeError("Something wrong with getting entity ids")

        try:
            entities = r.json()
        except JSONDecodeError:
            text = r.text
            text = text.replace(":inf", ":" + str(10**10))
            text = text.replace(":-inf", ":" + str(-(10**10)))

            entities = json.loads(text)

        if not entities:
            break

        ids = [i["id"] for i in entities]
        all_ids.extend(ids)
        if len(ids) < limit:
            break
        offset += limit
    return list(set(all_ids))


def get_entity(entity_id):
    r = session.get(f"{CB_URL}/ngsi-ld/v1/entities/{entity_id}", headers=POST_HEADERS)

    if not r.ok:
        raise KeyError(f'Entity: "{entity_id}" doesnt exist')

    entity = r.json()

    return entity


def entity_exists(entity_id):
    r = session.get(f"{CB_URL}/ngsi-ld/v1/entities/{entity_id}", headers=POST_HEADERS)
    return r.ok


def search_entity_name(search_string):
    all_ids = get_all_entity_ids()
    return [i for i in all_ids if search_string in i]


def get_entities(entities):
    block_size = 1000
    all_entities = []
    for i in range(0, len(entities), block_size):
        block_entities = entities[i : i + block_size]

        r = session.get(
            f"{CB_URL}/ngsi-ld/v1/entities?id={','.join(block_entities)}&limit=1000",
            headers=POST_HEADERS,
        )
        if not r.ok:
            pprint(r)
            pprint(r.json())
            if r.json()["title"] == "Invalid URI - no colon found":
                for i in block_entities:
                    print(i)
                    if ":" not in i:
                        print(i)
            else:
                print(r.json()["title"])

            raise KeyError("Something wrong with getting entities")
        try:
            entity_list = r.json()
        except JSONDecodeError:
            text = r.text
            text = text.replace(":inf", ":" + str(10**10))
            text = text.replace(":-inf", ":" + str(-(10**10)))
            try:
                entity_list = json.loads(text)
            except JSONDecodeError as e:
                print(text)
                raise e
        _id_list = [i["id"] for i in entity_list]

        didnt_get = set(block_entities) - set(_id_list)
        if len(didnt_get) > 0:
            raise KeyError(f"Didnt get the following entities: {didnt_get}")

        all_entities.extend(entity_list)

    return all_entities


def get_attributes(entity_id, keep_type=False):
    entity = get_entity(entity_id)
    if keep_type:
        drop = ["id"]
    else:
        drop = ["id", "type"]
    attributes = {key: value for (key, value) in entity.items() if key not in drop}
    return attributes


def create_entities_and_devices(
    entities: list, device_ids: list, block_size: int = 500
):
    CREATION_LOGGER.debug("Creating entities")
    create_entities(entities=entities, block_size=block_size)

    CREATION_LOGGER.debug("Creating devices")
    create_devices_from_entities(device_ids=device_ids)
    CREATION_LOGGER.debug(
        "Creating entities again, which have been overwritten by device creation"
    )
    create_entities(entities=entities, block_size=block_size)


def create_entities(entities: list, block_size: int = 500):
    existing_entities_in_platform = get_entities(get_all_entity_ids())
    existing_entities_in_platform_dict = {
        ent["id"]: ent for ent in existing_entities_in_platform
    }

    new_entities_dict = {ent["id"]: ent for ent in entities}

    push_entities = []
    for ent_id, ent in new_entities_dict.items():
        if ent_id not in existing_entities_in_platform_dict and not entity_exists(
            ent_id
        ):
            push_entities.append(ent)
        else:
            if ent_id in existing_entities_in_platform_dict:
                existing_attributes = set(
                    existing_entities_in_platform_dict[ent_id].keys()
                )
            else:
                existing_attributes = set(get_entity(ent_id).keys())
            new_attributes = {i for i in ent.keys() if i != "@context"}

            if len(new_attributes - existing_attributes) != 0:
                push_entities.append(ent)

    n_push = len(push_entities)
    if n_push == 0:
        CREATION_LOGGER.debug("All entities already exist!")
        return

    CREATION_LOGGER.debug(
        f"Creating/Updating {n_push} entities in blocks of {block_size}"
    )

    for i in range(0, len(push_entities), block_size):
        block = push_entities[i : i + block_size]
        block_ids = set([i["id"] for i in block])
        post_entities(entities=block)

        n = 0
        while True:
            if n >= 10:
                raise TimeoutError

            entities_in_platform = get_all_entity_ids()
            diff = set(block_ids) - set(entities_in_platform)

            if len(diff) == 0:
                CREATION_LOGGER.debug(f"Push of size {len(block)} successful")
                break

            actually_in_platform = True
            for _id in diff:
                if not entity_exists(_id):
                    actually_in_platform = False
                    break

            if actually_in_platform:
                CREATION_LOGGER.debug(
                    f"Push of size {len(block)} successful, even though some of the entities"
                    + " are not shown in the get_all_entity_ids() function"
                )
                break

            CREATION_LOGGER.debug(
                f"Push of size {len(block)} not successful. Retrying in 1 second"
            )

            post_entities(entities=block)
            n += 1
            time.sleep(1)


def delete_attributes(entity_id: str, attributes: list):
    """
    Kind of a stupid workaround, because has to get the entity first, then delete then post.
    But deleting attributes is a bit hard because of the stupid context, so this will work as well
    because it isnt needed that often anyway
    """
    entity = get_entity(entity_id)
    for attr in attributes:
        if attr in entity:
            del entity[attr]

    post_entities([entity])


def delete_scenario_attributes(entity_id: str, scenario_name: str):
    entity = get_entity(entity_id)
    del_attrs = []
    for key in entity:
        if f"_Scen_{scenario_name}" in key:
            del_attrs.append(key)

    for attr in del_attrs:
        del entity[attr]

    post_entities([entity])


def change_attributes(entity_id: str, attribute_dict: dict):
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload = {
        i: {"type": "Property", "value": j, "observedAt": current_time}
        for i, j in attribute_dict.items()
    }

    resp = session.post(
        f"{CB_URL}/ngsi-ld/v1/entities/{entity_id}/attrs",
        headers=POST_HEADERS_NO_LD,
        json=payload,
    )

    if not resp.ok:
        pprint(resp.json())
        raise TypeError("Error when posting entitys")

    if resp.status_code == 207:
        resp = resp.json()
        if len(resp["errors"]) > 0:
            pprint(resp)
            raise TypeError("Error when posting entitys")


def post_entities(entities):
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    for ent in entities:
        for attr in ent:
            if attr in ["id", "type", "@context"]:
                continue
            if ent[attr]["type"] == "Relationship":
                continue
            try:
                if ent[attr]["value"] == "":
                    continue
            except:  # noqa: E722
                pprint(ent)
                print(attr)
            if ent[attr]["type"] == "Property":
                if "observedAt" not in ent[attr]:
                    ent[attr]["observedAt"] = current_time

        if "@context" not in ent:
            ent["@context"] = ["http://context/ngsi-context.jsonld"]

    resp = session.post(
        f"{CB_URL}/ngsi-ld/v1/entityOperations/upsert",
        headers=POST_HEADERS,
        json=entities,
    )

    if not resp.ok:
        pprint(resp.json())
        raise TypeError("Error when posting entitys")

    if resp.status_code == 207:
        resp = resp.json()
        if len(resp["errors"]) > 0:
            pprint(resp)
            raise TypeError("Error when posting entitys")


def delete_all_entities_and_devices():
    while True:
        devices = get_devices()
        if len(devices) == 0:
            CREATION_LOGGER.debug("All devices deleted!")
            break
        CREATION_LOGGER.debug(f"Deleting {len(devices)} devices")
        device_ids = [i["device_id"] for i in devices]

        for _id in tqdm(device_ids):
            res = session.delete(url=IOTA_URL + f"/iot/devices/{_id}", headers=IOTA_HEADERS)

            if not res.ok:
                raise ConnectionError
        time.sleep(0.1)

    resp = session.delete(
        url=IOTA_URL + f"/iot/services/?resource=/iot/json&apikey={APIKEY}",
        headers=IOTA_HEADERS,
    )
    if not resp.ok:
        resp = resp.json()
        if resp["name"] != "DEVICE_GROUP_NOT_FOUND":
            pprint(resp.json())
            raise ConnectionError

    while True:
        all_entities = get_all_entity_ids()
        if len(all_entities) == 0:
            CREATION_LOGGER.debug("All entities deleted!")
            return
        CREATION_LOGGER.debug(f"Deleting {len(all_entities)} entities")
        delete_entities(all_entities)

        time.sleep(0.1)


def delete_entities(entities: list):
    res = session.post(
        f"{CB_URL}/ngsi-ld/v1/entityOperations/delete",
        headers=POST_HEADERS,
        json=entities,
    )

    if not res.ok:
        pprint(res.json())
        raise ConnectionError


def get_devices():
    devices = session.get(url=IOTA_URL + "/iot/devices", headers=IOTA_HEADERS).json()[
        "devices"
    ]

    return devices


def get_device_ids():
    return [i["device_id"] for i in get_devices()]


def create_devices_from_entities(device_ids: list):
    create_service_group()

    existing_entities_in_platform = get_entities(get_all_entity_ids())
    existing_entities_in_platform_dict = {
        ent["id"]: ent for ent in existing_entities_in_platform
    }
    devices = []

    for device_id in device_ids:
        entity_id = f"urn:ngsi-ld:{device_id}"
        if entity_id not in existing_entities_in_platform_dict and not entity_exists(
            entity_id
        ):
            CREATION_LOGGER.debug(
                f"Entity for device {device_id} not in platform. Wont create Device"
            )
            continue

        # here every entity should be in the platform, but not necessarily in the dict
        if entity_id not in existing_entities_in_platform_dict:
            entity = get_entity(entity_id)
        else:
            entity = existing_entities_in_platform_dict[entity_id]

        dev = {"transport": "MQTT"}

        dev["device_id"] = device_id
        dev["entity_name"] = entity_id
        dev["entity_type"] = entity["type"]
        attributes = []
        for attr, val in entity.items():
            if attr in ["id", "type", "@context"]:
                continue

            if val["type"] == "Relationship":
                continue

            if val["type"] != "Property":
                raise TypeError

            _attr = {"name": attr, "type": "Property"}

            attributes.append(_attr)

        dev["attributes"] = attributes
        devices.append(dev)

    devices_in_platform = get_devices()
    devices_id_in_platform = [i["device_id"] for i in devices_in_platform]

    to_push_devices = []
    delete_first = []
    for dev in devices:
        if dev in devices_in_platform:
            continue
        to_push_devices.append(dev)
        if dev["device_id"] in devices_id_in_platform:
            delete_first.append(dev["device_id"])

    for _id in delete_first:
        res = session.delete(url=IOTA_URL + f"/iot/devices/{_id}", headers=IOTA_HEADERS)

        if not res.ok:
            raise ConnectionError

    # to_push_devices = [i for i in devices if i['device_id'] not in devices_id_in_platform]

    if len(to_push_devices) == 0:
        CREATION_LOGGER.debug("All devices already exist!")
        return

    CREATION_LOGGER.debug(f"Creating {len(to_push_devices)} devices")

    for i in range(0, len(to_push_devices), 20):
        block = to_push_devices[i : i + 20]
        _devices = {"devices": block}
        resp = session.post(
            url=IOTA_URL + "/iot/devices", headers=IOTA_HEADERS, json=_devices
        )
        if not resp.ok:
            pprint(resp.json())
            raise TypeError("Error when creating devices")
        n = 0

        while True:
            if n >= 10:
                raise TimeoutError

            device_ids = set(get_device_ids())
            pushed_devices = set([i["device_id"] for i in block])

            diff = pushed_devices - device_ids

            if len(diff) == 0:
                break

            n += 1
            time.sleep(1)


def get_entities_of_type(entity_type: str):
    query_url = f"{CB_URL}/ngsi-ld/v1/entities"
    params = {"limit": 1000}
    if entity_type is not None:
        params["type"] = entity_type
    else:
        params["local"] = "true"

    response = session.get(query_url, headers=POST_HEADERS, params=params)

    if response.status_code != 200:
        print(f"Failed to query entities. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return

    entities = response.json()

    if not entities:
        print("No PredictionSetup entities found.")
        return

    return entities


def create_service_group():
    service_group = {
        "services": [
            {
                "apikey": APIKEY,
                "cbHost": "http://orion:1026",
                "entity_type": "Dummy",
                "resource": "/iot/json",
                "protocol": "IoTA-JSON",
                "timezone": "Europe/Berlin",
            }
        ]
    }

    resp = session.post(
        url=IOTA_URL + "/iot/services", headers=IOTA_HEADERS, json=service_group
    )

    if resp.ok:
        print("Service group created successfully.")
        return

    resp_json = resp.json()

    if resp_json.get("name") == "DUPLICATE_GROUP":
        print("Duplicate group found. Deleting existing group and creating a new one.")

        # Delete existing group
        delete_resp = session.delete(
            url=f"{IOTA_URL}/iot/services?resource=/iot/json&apikey={APIKEY}",
            headers=IOTA_HEADERS,
        )

        if not delete_resp.ok:
            print("Failed to delete existing group:")
            pprint(delete_resp.json())
            raise TypeError("Error when deleting existing service group")

        # Create new group
        create_resp = session.post(
            url=IOTA_URL + "/iot/services", headers=IOTA_HEADERS, json=service_group
        )

        if not create_resp.ok:
            print("Failed to create new group after deletion:")
            pprint(create_resp.json())
            raise TypeError("Error when creating new service group")

        print("New service group created successfully.")
        return

    print("Unexpected error occurred:")
    pprint(resp_json)
    raise TypeError("Error when creating service")


class EntityValueNoneError(Exception):
    pass


def get_values_from_fiware(get_from_fiware: list) -> Tuple[dict, str]:
    entities = get_entities(entities=list(set([f"urn:ngsi-ld:{i.split('//')[0]}" for i in get_from_fiware])))
    entities_dict = {i["id"]: i for i in entities}
    value_dict = {}
    youngest_timestamp = None

    something_is_none = False
    for var_name in get_from_fiware:
        ent_name, attr_name = var_name.split("//")
        ent_id = f"urn:ngsi-ld:{ent_name}"
        value = entities_dict[ent_id][attr_name]["value"]
        if value is None or value == "":
            something_is_none = True
            value = None

        value_dict[var_name] = value
        if something_is_none:
            continue
        timestamp = entities_dict[ent_id][attr_name]["observedAt"]
        if youngest_timestamp is None or timestamp > youngest_timestamp:
            youngest_timestamp = timestamp
    if something_is_none:
        message = "Some of the following value//attributes are still None:  \n"

        non_none_values_msg = "Non-None values:\n"
        none_values_msg = "None values:\n"
        for key, val in value_dict.items():
            if val is None:
                none_values_msg += f" - {key}\n"
            else:
                non_none_values_msg += f" - {key}: {val}\n"
        message += non_none_values_msg + none_values_msg
        raise EntityValueNoneError(message)

    return value_dict, youngest_timestamp


def validate_entities(to_check: list, check_attributes: bool) -> None:
    for var_name in to_check:
        ent_name, attr_name = var_name.split("//")
        # This will throw an error, if the entity does not exist
        entity = get_entity(entity_id=f"urn:ngsi-ld:{ent_name}")
        if not check_attributes:
            continue
        assert attr_name in entity, (
            f"Attribute {attr_name} does not exist in entity urn:ngsi-ld:{ent_name}"
        )


def validate_devices(push_to_fiware: list) -> None:
    device_ids = get_device_ids()
    for var_name in push_to_fiware:
        dev_id, _ = var_name.split("//")
        assert dev_id in device_ids, f"Device {dev_id} does not exist in the platform"


if __name__ == "__main__":
    print(get_device_ids())