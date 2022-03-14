#!/bin/bash
set -e

export DB_PASSWORD=123
export LETSENCRYPT_EMAIL=mail@example.com
export DOMAIN=127.0.0.1

./.github/scripts/generate-env.sh

docker-compose up -d
docker-compose exec -T backend bench new-site $DOMAIN --install-app comfort --db-root-password $DB_PASSWORD --admin-password admin

echo Ping version
ping_res=$(curl --insecure -sS "https://$DOMAIN/api/method/version")
echo "$ping_res"
if [[ -z $(echo "$ping_res" | grep "message" || echo "") ]]; then
  echo "Ping failed"
  exit 1
fi

echo Check index
index_res=$(curl --insecure -sS "https://$DOMAIN")
if [[ -n $(echo "$index_res" | grep "Internal Server Error" || echo "") ]]; then
  echo "Index check failed"
  echo "$index_res"
  exit 1
fi
