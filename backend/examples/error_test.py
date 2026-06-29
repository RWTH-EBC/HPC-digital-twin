import polars as pl
from pathlib import Path
import json
from it_zauber_digital_twin.agents_zih.infrastructure_agent.infrastructure_agent import InfrastructureAgent
from it_zauber_digital_twin.agents_zih.hpc_agent.hpc_agent import HPCAgent

def main():
    data_path = Path(__file__).parents[1] / "data" / "zih-example-data.parquet"
    data = pl.read_parquet(data_path)
    
    inf_config_path = Path(__file__).parents[1] / "src" / "it_zauber_digital_twin" / "agents_zih" / "infrastructure_agent" / "config.json"
    
    with open(inf_config_path, "r") as f:
        inf_config = json.load(f)
        
    get_from_fiware = inf_config["get_from_fiware"]
    
    names_in_df = [i[0].split("//")[0] for i in get_from_fiware]
    
    input_data = data.select(pl.col(["time"] + names_in_df))[0:1]
        
    
    rename = {i: f"{i}//value" for i in input_data.columns if i != "time"}
    input_data = input_data.rename(rename)
    
    hpc_agent = HPCAgent(offline_mode=True)
    ia = InfrastructureAgent(offline_mode=True)
    
    input_data = hpc_agent.predict(input_data)    
    res = ia.predict(input_data)
    print(res)
        
if __name__ == "__main__":
    main()