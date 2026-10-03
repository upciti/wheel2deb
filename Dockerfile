# Multi-stage build: build the binary in the first stage, copy to runtime image
# This ensures glibc compatibility with the target base image (Debian bookworm)

# Build stage
FROM wakemeops/debian:bookworm AS builder

ARG VERSION=""

# Install build dependencies
RUN install_packages \
    build-essential \
    fakeroot \
    debhelper \
    binutils-arm-linux-gnueabihf \
    binutils-aarch64-linux-gnu \
    git \
    ca-certificates \
    apt-file \
    curl \
    gnupg \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv

# Install Poetry via official installer (avoids PEP 668 issue)
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.2
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /build

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY src/ ./src/
COPY README.md ./

# Install dependencies and build binary
# Use VERSION build arg if provided (CI), else fallback to "0.0.0+dev"
# Note: poetry-dynamic-versioning requires .git which is excluded by .dockerignore
RUN poetry config virtualenvs.in-project true && \
    poetry install --extras pyinstaller --no-interaction && \
    if [ -n "$VERSION" ]; then poetry version "$VERSION" && echo "__version__ = \"$VERSION\"" > src/wheel2deb/version.py; else poetry version "0.0.0+dev" && echo '__version__ = "0.0.0+dev"' > src/wheel2deb/version.py; fi && \
    poetry run pyinstaller --onefile src/wheel2deb/__main__.py --name wheel2deb -s

# Runtime stage
FROM wakemeops/debian:bookworm

# Install runtime dependencies for building Debian packages
RUN install_packages \
    build-essential \
    fakeroot \
    debhelper \
    binutils-arm-linux-gnueabihf \
    binutils-aarch64-linux-gnu \
    git \
    ca-certificates \
    curl \
    gnupg \
    dpkg \
    dpkg-dev

RUN dpkg --add-architecture armhf && \
    dpkg --add-architecture arm64

# Copy the built binary from builder stage
COPY --from=builder /build/dist/wheel2deb /usr/local/bin/wheel2deb

# Create writable home/output directory for non-root user (UID 1000)
RUN mkdir -p /home/user/output && chown -R 1000:1000 /home/user
WORKDIR /home/user

ENTRYPOINT ["wheel2deb"]
USER 1000