# Dockerfile using uv only.
# DEPLOYMENT_ENV is a runtime variable (set via docker-compose environment: / .env).
# The image is built once; switching between itc/zih only requires changing .env - no rebuild.
# Julia is NOT installed at build time. For zih, the entrypoint installs it lazily into
# a named Docker volume at /opt/venv/julia_env on first start, then skips on subsequent starts.

FROM python:3.11-slim-bookworm

ENV IS_DOCKER=true

WORKDIR /app

# ============================================================
# Stage 1: System dependencies
# ============================================================
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# Stage 2: uv
# ============================================================
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"

# ============================================================
# Stage 3: Dependency files
# Cached layer - only invalidated when pyproject.toml or uv.lock change,
# NOT when source code changes.
# ============================================================
COPY pyproject.toml ./
COPY uv.lock* ./
COPY juliapkg.json* ./

# Install all Python dependencies (without the project itself).
# Runs before COPY src so this layer stays cached on source code changes.
RUN uv sync --frozen --no-install-project

# ============================================================
# Stage 4: Source code + project install
# ============================================================
COPY src ./src

# Install the project itself into the uv venv (fast, all deps already cached above).
RUN uv sync --frozen

# ============================================================
# Patch juliacall's juliapkg.json to allow Julia 1.12+
# juliacall ships an OpenSSL_jll compat bound "1.0.0 - 1.11" that blocks Julia 1.12.
# We remove the OpenSSL_jll entry entirely so juliapkg resolves Julia 1.12 without conflict.
# ============================================================
RUN python - <<'EOF'
import json, pathlib
p = pathlib.Path("/opt/venv/lib/python3.11/site-packages/juliacall/juliapkg.json")
data = json.loads(p.read_text())
data.get("packages", {}).pop("OpenSSL_jll", None)
data["julia"] = "^1.10.3"
p.write_text(json.dumps(data, indent=4))
print("Patched juliacall/juliapkg.json:", data)
EOF

# ============================================================
# Stage 5: Scripts and remaining application files
# ============================================================
COPY scripts ./scripts
COPY configs ./configs
COPY data ./data

# ============================================================
# Stage 6: Runtime environment variables
# ============================================================
ENV PATH="/opt/venv/bin:$PATH"
# juliapkg must stay offline at runtime; setup_env.py temporarily lifts this during setup
ENV PYTHON_JULIAPKG_OFFLINE="yes"
ENV PYTHON_JULIACALL_HANDLE_SIGNALS="yes"

# ============================================================
# Entrypoint: handles conditional ZIH julia setup at container start
# ============================================================
ENTRYPOINT ["sh", "/app/scripts/entrypoint.sh"]
CMD ["python", "--version"]
