#!/bin/bash
set -e
set -x

docker system prune -a -f

LOCAL_VERSION=$(docker-compose images | grep -P -o -m 1 -e "comfort-worker.*" | grep -P -o -e "v[^ ]+")
if [ $LOCAL_VERSION = $COMFORT_VERSION ]; then
  echo "No release should be made"
  exit 0
fi

docker-compose pull
docker-compose up -d --force-recreate --no-build --remove-orphans
docker-compose exec backend bench migrate
