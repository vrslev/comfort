FROM node:14-bullseye-slim as builder

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  git \
  ca-certificates \
  && if [ "$(uname -m)" = "aarch64" ]; then apt-get install --no-install-recommends -y python make g++; fi \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /home/frappe/frappe-bench

RUN mkdir -p apps sites/assets/css sites/assets/frappe sites/assets/comfort /var/www/error_pages \
  && echo "frappe\ncomfort" >> sites/apps.txt

RUN git clone --depth 1 --single-branch https://github.com/frappe/bench /tmp/bench \
  && cp -r /tmp/bench/bench/config/templates /var/www/error_pages

RUN git clone --depth 1 --single-branch https://github.com/frappe/frappe_docker /opt/frappe_docker

ARG FRAPPE_VERSION
RUN git clone --depth 1 -b $FRAPPE_VERSION https://github.com/frappe/frappe apps/frappe

COPY . apps/comfort

RUN cd apps/frappe \
  && echo "Install frappe Node dependencies..." \
  && yarn --pure-lockfile || true \
  && echo "Install comfort Node dependencies..." \
  && yarn --pure-lockfile --cwd ../comfort \
  && echo "Build frappe browser assets..." \
  && yarn production --app frappe \
  && echo "Build comfort browser assets..." \
  && yarn production --app comfort \
  && echo "Copy assets" \
  && cd /home/frappe/frappe-bench \
  && cp -R apps/comfort/comfort/public/* sites/assets/comfort \
  && cp -R apps/frappe/frappe/public/* sites/assets/frappe \
  && cp -R apps/frappe/node_modules sites/assets/frappe/


FROM nginx:1.21

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  rsync \
  && rm -rf /var/lib/apt/lists/*

RUN echo "#!/bin/bash" > /rsync \
  #   && echo "rsync -a --delete /var/www/html/assets/frappe /assets" >/rsync \
  #   && echo "rsync -a --delete /var/www/html/assets/comfort /assets" >>/rsync \
  && chmod +x /rsync

COPY --from=builder /home/frappe/frappe-bench/sites /var/www/html/
COPY --from=builder /var/www/error_pages /var/www/
COPY --from=builder /opt/frappe_docker/build/frappe-nginx/nginx-default.conf.template /etc/nginx/conf.d/default.conf.template
COPY --from=builder /opt/frappe_docker/build/frappe-nginx/docker-entrypoint.sh /

VOLUME [ "/assets" ]

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
