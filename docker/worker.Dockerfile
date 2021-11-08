ARG FRAPPE_VERSION
FROM frappe/frappe-worker:${FRAPPE_VERSION}

# Install Comfort
COPY --chown=frappe . ../apps/comfort
RUN ../env/bin/pip install --no-cache-dir -e ../apps/comfort

# Overwrite connection check commands
COPY --chown=frappe docker/scripts/check_connection.py docker/scripts/doctor.py ../commands/

VOLUME [ "/home/frappe/frappe-bench/sites", "/home/frappe/backups", "/home/frappe/frappe-bench/logs" ]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]
