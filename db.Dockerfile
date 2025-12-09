# db.Dockerfile (Final Build Fix)

# Start from the more stable Debian Slim image
FROM postgres:16-bullseye

# Set environment variables for the pgvector build process
ENV PG_CONFIG /usr/lib/postgresql/16/bin/pg_config

# Install necessary build tools and PostgreSQL development headers (Names change on Debian)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-server-dev-16 \
    git \
    cmake \
    libpq-dev \
    # MANDATORY FIX: Add ca-certificates to fix SSL/TLS handshake with GitHub
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone the pgvector source code (Now this will work!)
RUN git clone https://github.com/pgvector/pgvector.git

# Build and install pgvector (We keep the NO_LLVM flag just in case)
WORKDIR /pgvector
RUN make USE_PGXS=1 NO_LLVM=1
RUN make USE_PGXS=1 NO_LLVM=1 install

# Clean up build tools (MANDATE 2.2) - NOTE: apt cleanup is different
WORKDIR /
RUN apt-get purge -y build-essential postgresql-server-dev-16 git cmake \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*