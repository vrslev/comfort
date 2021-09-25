#!/bin/bash
set -e

ULINE="\e[1m\e[4m"
ENDULINE="\e[0m"
NEWLINE="\n"

function pingSite() {
  echo -e "${NEWLINE}${ULINE}Ping created site${ENDULINE}"
  ping_res=$(curl --insecure -sS https://test.localhost/api/method/version)
  echo $ping_res
  if [[ -z $(echo $ping_res | grep "message" || echo "") ]]; then
    echo "Ping failed"
    exit 1
  fi

  echo -e "${NEWLINE}${ULINE}Check Created Site Index Page${ENDULINE}"
  index_res=$(curl --insecure -sS https://test.localhost)
  if [[ -n $(echo $index_res | grep "Internal Server Error" || echo "") ]]; then
    echo $index_res
    echo "Index check failed"
    exit 1
  fi
}

export PROJECT_NAME=testcomfort

echo -e "${NEWLINE}${ULINE}Start Services${ENDULINE}"
ADMIN_PASSWORD=admin DB_PASSWORD=123 DOMAIN=test.localhost LETSENCRYPT_EMAIL=test@example.com \
  bash scripts/generate-env.sh
export $(cat .env)
docker-compose -p $PROJECT_NAME up -d

bash scripts/check-health.sh
pingSite

echo -e "${NEWLINE}${ULINE}Prune Containers${ENDULINE}"
docker-compose -p $PROJECT_NAME down
docker container prune -f
docker volume prune -f
