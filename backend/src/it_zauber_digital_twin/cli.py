"""
Command-line interface for running Digital Twin agents.

This module provides entry points for running individual agents in production.
"""

import argparse
import os
import sys


def run_preprocessing_agent_cli():
    """CLI entry point for preprocessing agent."""
    from it_zauber_digital_twin.utils.coordinator_loader import load_preprocessing_agent

    timestep = int(os.getenv("TIMESTEP", 5))
    agent = load_preprocessing_agent(timestep=timestep)
    agent.run()


def run_data_publisher_cli():
    """CLI entry point for data publisher agent."""
    from it_zauber_digital_twin.data_publishing_agent import DataPublishingAgent

    timestep = int(os.getenv("TIMESTEP", 5))

    agent = DataPublishingAgent(
        timestep=timestep,
    )
    agent.run()


def run_coordinator_cli():
    """CLI entry point for coordinator API."""
    import uvicorn
    from it_zauber_digital_twin.coordinator.api import create_app

    timestep = int(os.getenv("TIMESTEP", 5))
    real_time = int(os.getenv("RUN_LIVE", 0)) == 1

    app = create_app(timestep=timestep, real_time=real_time)
    uvicorn.run(app, host="0.0.0.0", port=8000)


def run_state_saver_cli():
    """CLI entry point for periodic state saver."""
    from it_zauber_digital_twin.periodic_state_saver import main as state_saver_main

    state_saver_main()


def main():
    """Main CLI entry point with agent selection."""
    parser = argparse.ArgumentParser(
        description="Run HPC Digital Twin agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --agent preprocessing_agent
  %(prog)s --agent data_publisher
  %(prog)s --agent coordinator
  %(prog)s --agent state_saver
  
Environment variables:
  TIMESTEP                  Timestep in seconds (default: 5)
  RUN_LIVE                  Run in real-time mode: 1=true, 0=false (default: 0)
  DEPLOYMENT_ENV            Deployment environment: zih, itc, ebc, local (default: local)
  STATE_SAVE_INTERVAL_HOURS Hours between FMU state saves (default: 24)
  COORDINATOR_URL           URL of coordinator API (default: http://coordinator:8000)
        """,
    )

    parser.add_argument(
        "--agent",
        type=str,
        required=True,
        choices=["preprocessing_agent", "data_publisher", "coordinator", "state_saver"],
        help="Agent type to run",
    )

    args = parser.parse_args()

    if args.agent == "preprocessing_agent":
        run_preprocessing_agent_cli()
    elif args.agent == "data_publisher":
        run_data_publisher_cli()
    elif args.agent == "coordinator":
        run_coordinator_cli()
    elif args.agent == "state_saver":
        run_state_saver_cli()
    else:
        parser.error(f"Unknown agent: {args.agent}")
        sys.exit(1)


if __name__ == "__main__":
    run_coordinator_cli()
