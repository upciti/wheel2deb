FROM python:3.8-buster AS builder
RUN apt-get -yq update \
 && apt-get -yq --no-install-suggests --no-install-recommends install \
    git \
 && apt-get clean
RUN git clone https://github.com/pi-top/wheel2deb /src
WORKDIR /src
RUN python3 setup.py bdist_wheel


FROM debian:buster AS base

RUN apt-get -yq update \
 && apt-get -yq --no-install-suggests --no-install-recommends install \
    libc6 \
    binutils-arm-linux-gnueabihf \
    build-essential \
    debhelper \
    devscripts \
    fakeroot \
    lintian \
    apt-file \
    python3-distutils \
    python3-apt \
    python3-pip \
    curl \
 && apt-get clean

RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir pytest pytest-cov

COPY --from=builder /src/dist/*.whl /
RUN pip3 install --no-cache-dir /*.whl && rm /*.whl

VOLUME /data
WORKDIR /data
ENTRYPOINT ["wheel2deb"]
