# syntax=docker/dockerfile:1
FROM python:3.11.5-slim-bookworm

# Install dumb-init and clean up apt leftovers
RUN apt-get update && apt-get install -y --no-install-recommends \
       dumb-init git openssh-client make \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create least-privilege group and user
RUN groupadd -g 999 edapdocker && \
    useradd -r -s /usr/bin/false -u 999 -g edapdocker edapdocker

RUN mkdir -p /usr/share/sample-data/
RUN chown 999 /usr/share/sample-data/

WORKDIR /emulate/edapgateway

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./ ./

USER 999

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python", "main.py"]