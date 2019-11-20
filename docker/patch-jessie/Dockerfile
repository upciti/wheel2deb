# dpkg-buildpackage is NOT idempotent on jessie. Building the same
# source package twice will result in different binaries.
# The packages in patch-jessie have been backported from stretch
# as a workaround to that issue.

FROM debian:jessie-slim
LABEL maintainer="fyhertz@gmail.com"

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

COPY *.deb /

RUN (apt-get -yq update || true) \
    && (dpkg -i /*.deb || true) \
    && apt-get -yq --no-install-recommends install -f \
    && rm -f /*.deb \
    && apt-get clean
