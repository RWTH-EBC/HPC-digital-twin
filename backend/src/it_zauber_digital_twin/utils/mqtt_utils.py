import json
import paho.mqtt.client as mqtt
from it_zauber_digital_twin.utils import get_iot_config
from it_zauber_digital_twin.utils.utils import setup_logger


class MQTTBroker:
    def __init__(self, host: str, port: int, apikey: str = None) -> None:
        """
        """
        client = mqtt.Client(protocol=mqtt.MQTTv5)
        client.connect(
                host=host,
                port=port,
                keepalive=60000,
                bind_address="",
                bind_port=0,
                clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,
                properties=None,
            )
        
        self.apikey = apikey
        self.client = client
        
        self.logger = setup_logger("MQTTBroker", level="WARNING")
    
    def publish(self, topic: str, payload: str) -> None:
        """Publish a message to a topic.

        Args:
            topic: The topic to publish to
            message: The message content
            sender: The ID of the sending entity
        """
        try:
            payload = json.dumps(payload)
            self.client.publish(topic, payload)
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")

    def publish_to_iot_agent(
        self, device_id: str, attribute_dict: str, timestamp: str = None
    ) -> None:
        if self.apikey is None:
            raise KeyError(
                "No API key found. Please set the API key before publishing to IoT Agent."
            )

        topic = f"json/{self.apikey}/{device_id}/attrs"
        if timestamp is not None:
            attribute_dict["TimeInstant"] = timestamp

        self.publish(topic, attribute_dict)
        
    def res_dict_to_iot_agent(
        self,
        res_dict: dict,
        timestamp: str,
        push_to_fiware: list[str] = None
    ) -> None:
        for variable_name, value in res_dict.items():
            if variable_name not in push_to_fiware:
                continue
            ent_name, attr_name = variable_name.split("//")
            
            self.logger.debug(f"Publishing {variable_name} with value {value} to IoT Agent")
            self.publish_to_iot_agent(
                device_id=ent_name,
                attribute_dict={attr_name: value},
                timestamp=timestamp,
            )
        


def get_mqtt_broker():
    iot_config = get_iot_config()

        
    for key in ["HOST", "MQTT_PORT", "APIKEY"]:
        assert key in iot_config, f"Missing '{key}' in IoT Agent config file."
        
    broker = MQTTBroker(
        host=iot_config["HOST"], port=iot_config["MQTT_PORT"], apikey=iot_config["APIKEY"])
    
    return broker



    