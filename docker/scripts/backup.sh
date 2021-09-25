# *Backup and push to S3 storage*
# Required environment variables:
# $BUCKET_NAME
# $REGION
# $ACCESS_KEY_ID
# $SECRET_ACCESS_KEY
# $ENDPOINT_URL

#!/bin/bash
set -e

export $(cat .env)

WORKER_IMAGE=cr.yandex/crpdmuh1072ntg30t18g/comfort-worker:$COMFORT_VERSION

docker run \
  -e WITH_FILES=1 \
  -v comfort_sites-vol:/home/frappe/frappe-bench/sites \
  --network comfort_default \
  $WORKER_IMAGE backup

# Keep backups for ~14 days
docker run \
  -e BUCKET_NAME=$BUCKET_NAME \
  -e REGION=$REGION \
  -e ACCESS_KEY_ID=$ACCESS_KEY_ID \
  -e SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY \
  -e ENDPOINT_URL=$ENDPOINT_URL \
  -e BUCKET_DIR=frappe-bench \
  -e BACKUP_LIMIT=70 \
  -v comfort_sites-vol:/home/frappe/frappe-bench/sites \
  --network comfort_default \
  $WORKER_IMAGE push-backup

echo "Local backups are removed"
docker run \
  -v comfort_sites-vol:/home/frappe/frappe-bench/sites \
  --network comfort_default \
  $WORKER_IMAGE bash -c "rm -rf /home/frappe/frappe-bench/sites/${DOMAIN}/private/backups/"
