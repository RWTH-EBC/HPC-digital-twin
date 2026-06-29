"""
Periodic State Saver for Infrastructure Agent FMU.

This module provides a background task that periodically saves the FMU state
of the Infrastructure Agent to disk, regardless of whether the agent is actively
running predictions or not.
"""

import os
import time
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

from it_zauber_digital_twin.utils.utils import setup_logger

load_dotenv()


class PeriodicStateSaver:
    """
    Periodically saves Infrastructure Agent FMU state via coordinator API.

    This runs as a separate process/container and calls the coordinator's
    /save_state endpoint at regular intervals (default: daily).
    """

    def __init__(
        self,
        coordinator_url: str = "http://coordinator:8000",
        save_interval_hours: int = 24,
        log_level: str = "INFO",
    ):
        """
        Initialize the periodic state saver.

        Args:
            coordinator_url: URL of the coordinator API
            save_interval_hours: Hours between state saves (default: 24 for daily)
            log_level: Logging level
        """
        self.coordinator_url = coordinator_url.rstrip("/")
        self.save_interval_hours = save_interval_hours
        self.save_interval_seconds = save_interval_hours * 3600
        self.logger = setup_logger("PeriodicStateSaver", level=log_level)

        self.logger.info(
            f"Initialized PeriodicStateSaver: "
            f"URL={coordinator_url}, "
            f"Interval={save_interval_hours}h"
        )

    def save_state(self) -> bool:
        """
        Trigger state save via coordinator API.

        Returns:
            True if successful, False otherwise
        """
        try:
            endpoint = f"{self.coordinator_url}/save_state"
            self.logger.info(f"Triggering state save via {endpoint}")

            response = requests.post(endpoint, timeout=30)
            response.raise_for_status()

            self.logger.info(f"State save successful at {datetime.now().isoformat()}")
            return True

        except requests.exceptions.ConnectionError as e:
            self.logger.error(
                f"Failed to connect to coordinator at {self.coordinator_url}: {e}"
            )
            return False

        except requests.exceptions.Timeout:
            self.logger.error(
                f"Timeout while connecting to coordinator at {self.coordinator_url}"
            )
            return False

        except requests.exceptions.HTTPError as e:
            self.logger.error(
                f"HTTP error during state save: {e.response.status_code} - {e.response.text}"
            )
            return False

        except Exception as e:
            self.logger.error(f"Unexpected error during state save: {e}")
            return False

    def run(self):
        """
        Main loop: periodically trigger state saves.

        Uses deadline-based scheduling similar to PreprocessingAgent to maintain
        consistent timing.
        """
        self.logger.info(
            f"Starting periodic state saver loop (every {self.save_interval_hours}h)"
        )

        start_time = time.perf_counter()
        deadline = start_time + self.save_interval_seconds

        while True:
            try:
                # Trigger state save
                success = self.save_state()

                if success:
                    next_save = datetime.now() + timedelta(
                        hours=self.save_interval_hours
                    )
                    self.logger.info(
                        f"Next state save scheduled for {next_save.isoformat()}"
                    )
                else:
                    self.logger.warning(
                        "State save failed, will retry at next interval"
                    )

            except Exception as e:
                self.logger.error(f"Error in state saver loop: {e}")

            # Calculate sleep time to maintain consistent interval
            current_time = time.perf_counter()
            sleep_time = deadline - current_time
            deadline += self.save_interval_seconds

            if sleep_time > 0:
                self.logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
            else:
                self.logger.warning(
                    f"State saver is lagging behind by {-sleep_time:.2f} seconds"
                )


def main():
    """CLI entry point for periodic state saver."""
    coordinator_url = os.getenv("COORDINATOR_URL", "http://coordinator:8000")
    save_interval_hours = int(os.getenv("STATE_SAVE_INTERVAL_HOURS", "24"))
    log_level = os.getenv("LOG_LEVEL", "INFO")

    saver = PeriodicStateSaver(
        coordinator_url=coordinator_url,
        save_interval_hours=save_interval_hours,
        log_level=log_level,
    )

    saver.run()


if __name__ == "__main__":
    main()
