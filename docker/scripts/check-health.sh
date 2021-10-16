set -e
set -x

ULINE="\e[1m\e[4m"
ENDULINE="\e[0m"
NEWLINE="\n"

echo -e "${NEWLINE}${ULINE}Loop Health Check${ENDULINE}"
echo "Create container to check health"
docker run \
  --name frappe_doctor \
  --network ${PROJECT_NAME}_default \
  -v ${PROJECT_NAME}_sites-vol:/home/frappe/frappe-bench/sites \
  cr.yandex/crpdmuh1072ntg30t18g/comfort-worker:$COMFORT_VERSION doctor || true

cmd='docker logs frappe_doctor | grep "Health check successful" || echo ""'
doctor_log=$(eval "$cmd")
while [[ -z "${doctor_log}" ]]; do
  sleep 1
  container=$(docker start frappe_doctor)
  echo "Restarting ${container}"
  doctor_log=$(eval "$cmd")
done
echo "Health check successful"

cmd='docker logs ${PROJECT_NAME}_site-creator_1 | grep "Scheduler is disabled\|already exists" || echo ""'
site_creator_log=$(eval "$cmd")
while [[ -z "${site_creator_log}" ]]; do
  sleep 3
  echo "Waiting for site creation"
  site_creator_log=$(eval "$cmd")
  echo "$site_creator_log"
done
echo "Site created"

docker stop frappe_doctor >/dev/null
docker rm frappe_doctor >/dev/null
