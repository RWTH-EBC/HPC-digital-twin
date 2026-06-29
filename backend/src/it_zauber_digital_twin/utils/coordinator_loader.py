from dotenv import load_dotenv
import os
from it_zauber_digital_twin.coordinator.coordinator_itc import CoordinatorITC
from it_zauber_digital_twin.coordinator.coordinator_zih import CoordinatorZIH


load_dotenv()

def which_deployment_env():
    env_name = os.getenv("DEPLOYMENT_ENV", "itc")  # Default to 'local' if not set
    if env_name not in ["local", "zih", "itc", "ebc"]:
        raise ValueError(
            f"Unknown DEPLOYMENT_ENV: {env_name}. Must be one of 'local', 'zih', 'itc', 'ebc'."
        )
        
    if env_name in ["local", "ebc"]:
        env_name = "itc"  # Use itc config for local and ebc deployments
        
    return env_name

def load_preprocessing_agent(timestep: int):
    env_name = which_deployment_env()
    if env_name == "itc":
        from it_zauber_digital_twin.agents_itc import PreprocessingAgent
        return PreprocessingAgent(timestep=timestep)
    elif env_name == "zih":
        from it_zauber_digital_twin.agents_zih import PreprocessingAgent
        return PreprocessingAgent(timestep=timestep)
    else:
        raise ValueError(f"Unsupported DEPLOYMENT_ENV: {env_name}")


def load_coordinator(timestep: int, real_time: bool):
    env_name = which_deployment_env()
    if env_name == "itc":
        return load_itc_coordinator(timestep=timestep, real_time=real_time)
    elif env_name == "zih":
        return load_zih_coordinator(timestep=timestep, real_time=real_time)
    else:
        raise ValueError(f"Unsupported DEPLOYMENT_ENV: {env_name}")


def load_itc_coordinator(timestep: int, real_time: bool):
    from it_zauber_digital_twin.agents_itc import (
        HPCAgent,
        InfrastructureAgent,
    )

    coordinator = CoordinatorITC(
        coordinated_agents={
            "hpc_agent": {"class": HPCAgent, "position": 0},
            "infrastructure_agent": {"class": InfrastructureAgent, "position": 1},
        },
        timestep=timestep,
        real_time=real_time,
    )
    return coordinator


def load_zih_coordinator(timestep: int, real_time: bool):
    from it_zauber_digital_twin.agents_zih import (
        HPCAgent,
        InfrastructureAgent,
    )
    coordinator = CoordinatorZIH(
        coordinated_agents={
            "hpc_agent": {"class": HPCAgent, "position": 0},
            "infrastructure_agent": {"class": InfrastructureAgent, "position": 1},
        },
        timestep=timestep,
        real_time=real_time,
    )
    return coordinator
