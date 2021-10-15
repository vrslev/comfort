#!/bin/bash
set -e

docker system prune -a -f
docker-compose pull
docker-compose up -d --force-recreate --no-build --remove-orphans

PROJECT_NAME=comfort bash scripts/check-health.sh

docker run \
  -e MAINTENANCE_MODE=1 \
  -v comfort_sites-vol:/home/frappe/frappe-bench/sites \
  -v comfort_assets-vol:/home/frappe/frappe-bench/sites/assets \
  --network comfort_default \
  --rm \
  cr.yandex/crpdmuh1072ntg30t18g/comfort-worker:$COMFORT_VERSION migrate
