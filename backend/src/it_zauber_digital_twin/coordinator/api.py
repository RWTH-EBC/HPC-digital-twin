"""
FastAPI wrapper for the Coordinator to enable REST API access.

This module provides a FastAPI interface to trigger coordinator functionality
(like predictions) via HTTP endpoints instead of MQTT messages, while keeping
the coordinator class unchanged.
"""

import os
import pprint
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from it_zauber_digital_twin.coordinator.coordinator import Coordinator
from it_zauber_digital_twin.utils.utils import setup_logger

from it_zauber_digital_twin.utils.coordinator_loader import load_coordinator

class CoordinatorAPI:
    """
    FastAPI wrapper for the Coordinator.

    This class manages a Coordinator instance and provides REST API endpoints
    to interact with it. The coordinator can run in a background thread while
    serving API requests.
    """

    def __init__(
        self,
        timestep: int = 5,
        real_time: bool = False,
        auto_start: bool = False,
    ):
        """
        Initialize the CoordinatorAPI.

        Args:
            config_path: Path to the IoT configuration file. If None, uses default path.
            enable_mqtt: Whether to enable MQTT functionality in the coordinator.
            timestep: Timestep for the coordinator in seconds.
            real_time: Whether to run in real-time mode.
            auto_start: Whether to automatically start the coordinator's main loop on startup.
        """
        self.logger = setup_logger(__name__)
        self.coordinator: Optional[Coordinator] = None
        self.coordinator_thread: Optional[threading.Thread] = None
        self.timestep = timestep
        self.real_time = real_time
        self.auto_start = auto_start

        # Create lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup: Initialize coordinator
            self.initialize_coordinator()
            if self.auto_start:
                self.coordinator_thread = threading.Thread(
                    target=self.coordinator.run,
                    daemon=True,
                )
                self.coordinator_thread.start()
                self.logger.info("Coordinator main loop started automatically")
            yield
            # Shutdown: Cleanup
            self.logger.info("Shutting down coordinator...")
            if self.coordinator:
                try:
                    self.coordinator.save_modelica_state()
                    self.logger.info("Saved Modelica state on shutdown")
                except Exception as e:
                    self.logger.error(f"Failed to save Modelica state on shutdown: {e}")
            self.stop_coordinator()

        # Create FastAPI app with lifespan
        self.app = FastAPI(
            title="Digital Twin Coordinator API",
            description="REST API for controlling the Digital Twin Coordinator",
            version="1.0.0",
            lifespan=lifespan,
        )

        # Add CORS middleware - allow all origins (no security)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "*"
            ],  # Allow all origins (React dashboard can access from anywhere)
            allow_credentials=True,
            allow_methods=["*"],  # Allow all HTTP methods (GET, POST, DELETE, etc.)
            allow_headers=["*"],  # Allow all headers
        )

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/", response_model=Dict[str, str])
        async def root():
            """Root endpoint."""
            return {
                "message": "Digital Twin Coordinator API",
                "version": "1.0.0",
                "docs": "/docs",
            }

        @self.app.get("/optimize/status")
        async def get_optimization_status():
            """Get the current status of the optimization process."""
            if self.coordinator is None:
                raise HTTPException(
                    status_code=503, detail="Coordinator not initialized"
                )

            # Convert Manager dict to regular dict for JSON serialization
            return dict(self.coordinator.optimization_status)

        @self.app.post("/predict")
        async def predict(request: Dict[str, Any]):
            """
            Trigger a prediction with the given scenarios.

            This endpoint triggers the prediction process in the background,
            similar to how it would be triggered via MQTT.

            Request body should be:
            {
                "scenarios": [
                    {
                        "templateName": "scenario-name",
                        "convertFromDashboard": true/false (optional, default: false),
                        "scenario_settings": {
                            // Any parameters your system needs
                            "param1//value": value1,
                            "n_steps": 24,
                            ...
                        }
                    }
                ]
            }
            """
            if self.coordinator is None:
                raise HTTPException(
                    status_code=503, detail="Coordinator not initialized"
                )

            # Check if prediction is already running
            prediction_status = self.coordinator.get_prediction_status()
            if prediction_status.get("is_running", False):
                return {
                    "status": "already_running",
                    "message": "Prediction is already running, request not started",
                    "prediction": {
                        "started_at": prediction_status.get("started_at"),
                        "elapsed_seconds": prediction_status.get("elapsed_seconds"),
                    },
                    "timestamp": datetime.now().isoformat(),
                }

            try:
                scenario_dicts = request.get("scenarios", [])

                if not scenario_dicts:
                    self.logger.error(request)
                    raise HTTPException(status_code=400, detail="No scenarios provided")

                # Call the predict method (it spawns its own process)
                self.coordinator.predict(scenario_dicts=scenario_dicts)

                return {
                    "status": "success",
                    "message": f"Prediction started for {len(request)} scenario(s)",
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                self.logger.error(f"Error during prediction: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Prediction failed: {str(e)}"
                )

        @self.app.post("/optimize")
        async def optimize(request: Dict[str, Any]):
            """
            Trigger an optimization with the given scenarios.

            This endpoint triggers the optimization process in the background,
            similar to h ow it would be triggered via MQTT.

            Request body should be:
            {

                "templateName": "scenario-name",
                "scenario_settings": {
                    // Any parameters your system needs
                    "param1//value": value1,
                    "n_steps": 24,
                    ...
                }
            }
            """
            if self.coordinator is None:
                raise HTTPException(
                    status_code=503, detail="Coordinator not initialized"
                )

            try:
                opt_dict = request

                if not opt_dict:
                    raise HTTPException(status_code=400, detail="No scenario provided")

                self.logger.error("Starting optimization dummy...")
                if opt_dict:
                    self.logger.error(f"Scenario dict:\n{pprint.pformat(opt_dict)}")
                # Call the optimize method (it spawns its own process)
                start_time = datetime.now()
                duration = opt_dict.get("optimization_settings", {}).get("opt_time", 0)
                end_time = start_time + timedelta(seconds=duration)
                self.coordinator.optimization_status.update(
                    {
                        "started_at": start_time.isoformat(),
                        "expected_end_time": end_time.isoformat(),
                        "opt_name": opt_dict.get("opt_name", "unknown"),
                        "progress": 0,
                        "remaining_time": duration,
                        "opt_time": duration,
                        "n_evals": 0,
                    }
                )

                self.coordinator.optimize(optimizer_settings=opt_dict)

                self.coordinator.optimization_status.update(
                    {"is_running": True, "is_finished": False}
                )

                return {
                    "status": "success",
                    "message": "Optimization started",
                    "start_time": start_time.isoformat(),
                    "expected_end_time": end_time.isoformat(),
                }
            except Exception as e:
                self.logger.error(f"Error during optimization: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Optimization failed: {str(e)}"
                )

        @self.app.delete("/optimize/stop")
        async def stop_optimization():
            """
            Stop the currently running optimization process.
            """
            if self.coordinator is None:
                raise HTTPException(
                    status_code=503, detail="Coordinator not initialized"
                )

            stopped = self.coordinator.stop_optimization()

            if stopped:
                return {
                    "status": "success",
                    "message": "Optimization process terminated",
                    "timestamp": datetime.now().isoformat(),
                    "res_obj": dict(self.coordinator.optimization_status),
                }
            else:
                return {
                    "status": "warning",
                    "message": "No running optimization process found",
                    "timestamp": datetime.now().isoformat(),
                }

        @self.app.post("/save_state")
        async def save_state():
            """
            Trigger saving the Modelica FMU state.
            """
            if not self.coordinator:
                raise HTTPException(status_code=503, detail="Coordinator not initialized")

            try:
                self.coordinator.save_modelica_state()
                return {"status": "success", "message": "Modelica state save triggered"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        #TODO: move that directly to dashboard
        @self.app.delete("/template/{template_name}")
        async def delete_template(template_name: str):
            """
            Delete template data from InfluxDB.

            Args:
                template_name: Name of the template to delete, or 'all' to delete all templates.
            """
            if self.coordinator is None:
                raise HTTPException(
                    status_code=503, detail="Coordinator not initialized"
                )

            try:
                if template_name == "all":
                    self.coordinator.influx_agent.delete_template_data()
                    message = "Deleted all scenario data"
                else:
                    self.coordinator.influx_agent.delete_template_data(
                        template_name=template_name
                    )
                    message = f"Deleted template data for {template_name}"

                return {
                    "status": "success",
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                self.logger.error(f"Error deleting template: {e}")
                raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

    def initialize_coordinator(self):
        """
        Initialize the coordinator instance.

        Args:
            debug_one_step: Whether to run in debug mode (single step).
        """

        self.coordinator = load_coordinator(
            timestep=self.timestep,
            real_time=self.real_time,
        )

        self.logger.info("Coordinator initialized")

    def stop_coordinator(self):
        """Stop the coordinator if it's running."""
        if self.coordinator_thread and self.coordinator_thread.is_alive():
            # Note: This is a graceful approach; for forceful stop, you'd need
            # to implement a stop flag in the coordinator's run loop
            self.logger.info("Coordinator thread is daemon, will stop on app shutdown")


def create_app(
    timestep: Optional[int] = None,
    real_time: Optional[bool] = None,
    auto_start: bool = True,
) -> FastAPI:
    """
    Factory function to create a configured FastAPI app.

    Args:
        timestep: Timestep for the coordinator in seconds. If None, reads from TIMESTEP env var (default: 5).
        real_time: Whether to run in real-time mode. If None, reads from RUN_LIVE env var (default: False).
        auto_start: Whether to automatically start the coordinator's main loop on startup.

    Returns:
        Configured FastAPI application.
    """
    # Read from environment variables if not provided
    if timestep is None:
        timestep = int(os.getenv("TIMESTEP", "5"))

    if real_time is None:
        run_live = int(os.getenv("RUN_LIVE", "0"))
        real_time = run_live == 1

    coordinator_api = CoordinatorAPI(
        timestep=timestep,
        real_time=real_time,
        auto_start=auto_start,
    )
    return coordinator_api.app
