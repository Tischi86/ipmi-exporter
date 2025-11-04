FROM python:2.7

# Python deps
RUN pip install prometheus_client

# Buster ist im Archiv -> Sources umstellen + Valid-Until-Check aus
RUN set -eux; \
    sed -i 's|deb.debian.org/debian|archive.debian.org/debian|g' /etc/apt/sources.list; \
    sed -i 's|security.debian.org/debian-security|archive.debian.org/debian-security|g' /etc/apt/sources.list; \
    printf 'Acquire::Check-Valid-Until "false";\n' > /etc/apt/apt.conf.d/99no-check-valid; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update; \
    apt-get install -y --no-install-recommends ipmitool; \
    rm -rf /var/lib/apt/lists/*

COPY ipmi_exporter.py /

# Set environment variables
ENV TARGET_IPS=""

EXPOSE 8000

CMD ["python", "ipmi_exporter.py"]
