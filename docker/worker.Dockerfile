ARG FRAPPE_VERSION
FROM frappe/frappe-worker:${FRAPPE_VERSION}

COPY --chown=frappe setup.py ../apps/comfort/
# TODO: Mount cache
RUN ../env/bin/pip install --no-cache-dir -e ../apps/comfort

COPY --chown=frappe . ../apps/comfort
# Overwrite connection check commands
COPY --chown=frappe docker/scripts/check_connection.py docker/scripts/doctor.py ../commands/
# Overwrite docker-entrypoint.sh
COPY --chown=frappe docker/scripts/worker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

VOLUME [ "/home/frappe/frappe-bench/sites", "/home/frappe/backups", "/home/frappe/frappe-bench/logs" ]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]
