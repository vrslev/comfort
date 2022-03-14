# Backup and push to S3 storage

set -e
set -x

if [[ -z "$(docker network ls | grep comfort_default)" ]]; then
  exit 0
fi

docker-compose exec backend bench --site $DOMAIN backup --with-files
docker-compose exec backend push-backup \
  --site $DOMAIN \
  --bucket $BUCKET_NAME \
  --region-name $REGION \
  --endpoint-url $ENDPOINT_URL \
  --aws-access-key-id $ACCESS_KEY_ID \
  --aws-secret-access-key $SECRET_ACCESS_KEY
