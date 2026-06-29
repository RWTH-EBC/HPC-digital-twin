import json
from pathlib import Path

from it_zauber_digital_twin.utils.fiware_utils import (
    create_entities_and_devices,
    delete_all_entities_and_devices,
)

def device_ids_from_entities(entities: list) -> list:
    return [i["id"].split(":")[-1] for i in entities]

def delete_and_create():
    itc_entities_p = Path(__file__).parent / "itc_entities.json"
    zih_entities_p = Path(__file__).parent / "zih_entities.json"
    with open(itc_entities_p, "r") as f:
        itc_entities = json.load(f)

    with open(zih_entities_p, "r") as f:
        zih_entities = json.load(f)
        
    itc_ids = [i["id"] for i in itc_entities]
    zih_entities = [i for i in zih_entities if i["id"] not in itc_ids]
    
    entities = itc_entities + zih_entities
    device_ids = device_ids_from_entities(entities)

    delete_all_entities_and_devices()
    create_entities_and_devices(
        entities=entities, device_ids=device_ids, block_size=1000
    )
           
if __name__ == "__main__":
    delete_and_create()
    
