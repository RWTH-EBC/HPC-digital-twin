import requests as r
from it_zauber_digital_twin.utils.config_loader import get_iot_config

HOST = get_iot_config().get("HOST", "localhost")


def main_itc():
    body = {
        "scenarios": [
            {"templateName": "test",
             "scenario_settings": {
                 "wt03_water_temperature_cold_facility_side_manual_setpoint//value"
                 : 25
                 },
             "fmu_settings": {
                    "stepsize": 120,
                    "sim_days": 1
             }
             }
        ]
    }
    
    r.post(f"http://{HOST}:8000/predict", json=body)
    
def main_zih():
    body = {
        "scenarios": [
            {"templateName": "test",
             "scenario_settings": {
                 "LZR.K21.KKR01.B08//value"
                 : 25
                 },
             "fmu_settings": {
                    "stepsize": 120,
                    "sim_days": 1
             }
             }
        ]
    }
    
    r.post(f"http://{HOST}:8000/predict", json=body)
    
if __name__ == "__main__":
    main_itc()