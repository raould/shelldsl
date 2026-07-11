#!/bin/sh

# Build and run minimal.py in every Python Dockerfile under VM/test/docker.
# The script deliberately uses the repository root as Docker's build context
# so each Dockerfile can COPY VM into the image.

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TEST_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_DIR=$(CDPATH= cd -- "$TEST_DIR/../.." && pwd)
DOCKER_DIR="$TEST_DIR/docker"

if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker is required" >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "error: the current user cannot access the Docker daemon" >&2
    echo "hint: add the user to the docker group, then start a new login session:" >&2
    echo "  sudo usermod -aG docker \"$(id -un)\"" >&2
    echo "  newgrp docker" >&2
    echo "alternative: run this script through a root-authorized Docker context" >&2
    exit 1
fi

found=0

for dockerfile in "$DOCKER_DIR"/Dockerfile.py_*; do
    if [ ! -f "$dockerfile" ]; then
        continue
    fi

    found=1
    filename=$(basename "$dockerfile")
    version=${filename#Dockerfile.}
    image="shelldsl-vm-${version}"

    echo "==> Building $image from $filename"
    docker build \
        --file "$dockerfile" \
        --tag "$image" \
        "$REPO_DIR"

    echo "==> Running VM/test/minimal.py with $image"
    docker run --rm --network none \
        "$image" \
        python "VM/test/minimal.py"
done

if [ "$found" -eq 0 ]; then
    echo "error: no Dockerfile.py_* files found in $DOCKER_DIR" >&2
    exit 1
fi

echo "All minimal tests passed."
