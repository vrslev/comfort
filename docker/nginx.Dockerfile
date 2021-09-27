ARG FRAPPE_VERSION
FROM node:14-buster-slim as builder

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  git \
  ca-certificates \
  && if [ "$(uname -m)" = "aarch64" ]; then apt-get install --no-install-recommends -y python make g++; fi \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /home/frappe/frappe-bench
RUN mkdir -p sites/assets/frappe sites/assets/comfort apps \
  && echo "frappe\ncomfort" >> sites/apps.txt

ARG FRAPPE_VERSION
RUN git clone --depth 1 -b ${FRAPPE_VERSION} https://github.com/frappe/frappe apps/frappe

COPY . apps/comfort

RUN cd apps \
  && echo "Install frappe NodeJS dependencies . . ." \
  && yarn --pure-lockfile --cwd frappe || true \
  && echo "Install comfort NodeJS dependencies . . ." \
  && yarn --pure-lockfile --cwd comfort || true \
  && echo "Build comfort browser assets . . ." \
  && cd frappe \
  && yarn production --app comfort \
  && echo "Install frappe NodeJS production dependencies . . ." \
  && yarn --pure-lockfile --prod \
  && echo "Install comfort NodeJS production dependencies . . ." \
  && cd ../comfort \
  && yarn --pure-lockfile --prod \
  && echo "Copy assets" \
  && cd /home/frappe/frappe-bench \
  && mkdir -p sites/assets/comfort \
  && cp -R apps/comfort/comfort/public/* sites/assets/comfort \
  && echo "rsync -a --delete /var/www/html/assets/frappe /assets" > /rsync \
  && echo "rsync -a --delete /var/www/html/assets/comfort /assets" >> /rsync \
  && chmod +x /rsync


FROM frappe/frappe-nginx:${FRAPPE_VERSION}

COPY --from=builder /home/frappe/frappe-bench/sites/ /var/www/html/
COPY --from=builder /rsync /rsync

VOLUME ["/assets"]

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]