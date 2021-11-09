set -e

source .env

dir=/tmp/frappe_docker
git clone --depth 1 https://github.com/frappe/frappe_docker $dir
docker build $dir \
  -f $dir/build/frappe-socketio/Dockerfile \
  -t frappe/frappe-socketio:$FRAPPE_VERSION
rm -rf $dir
