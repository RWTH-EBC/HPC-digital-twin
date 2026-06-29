import multiprocessing as mp
import signal
import sys

import uvicorn

from it_zauber_digital_twin.coordinator.api import create_app
from it_zauber_digital_twin.utils.coordinator_loader import load_preprocessing_agent
from it_zauber_digital_twin.agents_itc import DataPublishingAgent


def main(timestep: int = 20, real_time: bool = True, with_coordinator: bool = True):
    """
    Run both data publisher and coordinator API.

    Data publisher runs in a separate process.
    Coordinator API runs in the main process (keeps it alive via uvicorn).
    """
    # Start data publisher in background process
    data_publisher_process = mp.Process(
        target=run_data_publisher,
        args=(timestep, real_time),
        name="DataPublisher",
        daemon=True,  # Will automatically terminate when main process exits
    )
    
    preprocessing_process = mp.Process(
        target=run_preprocessing_agent,
        args=(timestep,),
        name="PreprocessingAgent",
        daemon=True,
    )
    
    def signal_handler(signum, frame):
        print("\nShutting down...")
        if data_publisher_process.is_alive():
            data_publisher_process.terminate()
            data_publisher_process.join(timeout=5)
        if preprocessing_process.is_alive():
            preprocessing_process.terminate()
            preprocessing_process.join(timeout=5)
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    data_publisher_process.start()
    print("Started DataPublisher process")
    print("Starting Preprocessing Agent...")
    
    if with_coordinator:
        preprocessing_process.start()
    else:
        # This will block the main process, so only use if coordinator is not run
        run_preprocessing_agent(timestep=timestep)
        return
    
    print("Starting Coordinator API...")
    print("API will be available at: http://localhost:8000")

    # Setup signal handler for graceful shutdown
    # Run coordinator API in main process (blocking)
    # This keeps the main process alive
    run_coordinator_api(timestep=timestep, real_time=real_time)


def run_data_publisher(timestep: int = 5, real_time: bool = False):
    agent = DataPublishingAgent(
        offline_mode=False,
        timestep=timestep,
        real_time=real_time,
    )
    agent.run()


def run_preprocessing_agent(timestep: int = 5):
    agent = load_preprocessing_agent(timestep=timestep)
    agent.run()
    

def run_coordinator_api(timestep: int = 5, real_time: bool = False):
    """
    Run the coordinator as a FastAPI application.

    Args:
        debug: If True, enables debug mode and auto-triggers a test prediction
        timestep: Timestep for the coordinator in seconds
        real_time: Whether to run in real-time mode
    """
    app = create_app(
        timestep=timestep,
        real_time=real_time,
        auto_start=True,  # Start MQTT listener automatically
    )

    # Run uvicorn server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    run_preprocessing_agent()
    # Run both data publisher and coordinator API
    # main(with_coordinator=False)
