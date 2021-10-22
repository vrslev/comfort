set -e
set -x

docker system prune -a -f

LOCAL_VERSION=$(awk -F'=' '/COMFORT_VERSION/{ print $2 }' .env)
if [ LOCAL_VERSION = COMFORT_VERSION ]; then
  echo "No release should be made"
  exit 0
fi;

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
