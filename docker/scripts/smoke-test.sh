set -e

print_group() {
  echo ::endgroup::
  echo "::group::$*"
}

if [ -z $CI ]; then
  DOMAIN=127.0.0.1
else
  DOMAIN=test.localhost
fi

export PROJECT_NAME=testcomfort

# Initial group
echo ::group::Generate .env
ADMIN_PASSWORD=admin \
  DB_PASSWORD=123 \
  DOMAIN=$DOMAIN \
  LETSENCRYPT_EMAIL=test@example.com \
  bash scripts/generate-env.sh
cat .env
export $(cat .env)

print_group Start services
docker-compose -p $PROJECT_NAME up -d

print_group Check health
bash scripts/check-health.sh

print_group Ping site

echo Ping version
ping_res=$(curl --insecure -sS "https://$SITE_NAME/api/method/version")
echo "$ping_res"
if [[ -z $(echo "$ping_res" | grep "message" || echo "") ]]; then
  echo "Ping failed"
  exit 1
fi

echo Check index
index_res=$(curl --insecure -sS "https://$SITE_NAME")
if [[ -n $(echo "$index_res" | grep "Internal Server Error" || echo "") ]]; then
  echo "Index check failed"
  echo "$index_res"
  exit 1
fi

if [ -z $CI ]; then
  print_group Prune containers
  docker-compose -p $PROJECT_NAME down -v --remove-orphans
fi

rm -rf .env
