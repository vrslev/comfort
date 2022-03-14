ARG FRAPPE_VERSION
FROM frappe/frappe-worker:${FRAPPE_VERSION}

COPY --chown=frappe . ../apps/comfort

# TODO: Cache doesn't work
RUN --mount=type=cache,target=/home/frappe/.cache/pip echo "frappe\ncomfort" >/home/frappe/frappe-bench/sites/apps.txt \
  && ../env/bin/pip install -e ../apps/comfort

# Overwrite connection check commands
COPY --chown=frappe docker/scripts/check_connection.py docker/scripts/doctor.py ../commands/
# Overwrite docker-entrypoint.sh
COPY --chown=frappe docker/scripts/worker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
