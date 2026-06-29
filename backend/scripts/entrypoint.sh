#!/bin/sh
set -e

# Julia setup is only needed for the coordinator service running in zih mode.
if [ "${DEPLOYMENT_ENV}" = "zih" ] && [ "${ENABLE_JULIA_SETUP}" = "true" ]; then
    JULIA_BIN="/opt/venv/julia_env/pyjuliapkg/install/bin/julia"
    if [ -x "${JULIA_BIN}" ]; then
        echo "[entrypoint] Julia/ZIHsim already installed, skipping setup."
    else
        echo "[entrypoint] Julia binary not found, running setup_env.py..."
        /opt/venv/bin/python /app/scripts/setup_env.py
        echo "[entrypoint] Setup complete."
    fi
fi

exec "$@"
