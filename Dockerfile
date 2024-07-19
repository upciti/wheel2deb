FROM wakemeops/debian:bookworm

ARG WHEEL2DEB_PATH="dist/wheel2deb"
COPY ${WHEEL2DEB_PATH} /usr/local/bin/wheel2deb

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
    gnupg

RUN dpkg --add-architecture armhf && \
    dpkg --add-architecture arm64

ENTRYPOINT ["wheel2deb"]
USER 1000
