ARG FRAPPE_VERSION
FROM node:14-bullseye-slim as prod_node_modules

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
  git \
  build-essential \
  python \
  ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /root/frappe-bench
RUN mkdir -p sites/assets

ARG FRAPPE_VERSION
RUN git clone --depth 1 -b ${FRAPPE_VERSION} https://github.com/frappe/frappe apps/frappe

RUN yarn --cwd apps/frappe


COPY . apps/comfort

# Install production node modules
RUN yarn --cwd apps/comfort --prod



FROM prod_node_modules as assets

# Install development node modules
RUN yarn --cwd apps/comfort

# Build assets
RUN echo "frappe\ncomfort" >sites/apps.txt \
  && yarn --cwd apps/frappe production --app comfort \
  && rm sites/apps.txt



FROM frappe/frappe-nginx:${FRAPPE_VERSION}

# Copy all not built assets
COPY --from=prod_node_modules /root/frappe-bench/apps/comfort/comfort/public /usr/share/nginx/html/assets/comfort
# Copy production node modules
COPY --from=prod_node_modules /root/frappe-bench/apps/comfort/node_modules /usr/share/nginx/html/assets/comfort/node_modules
# Copy built assets
COPY --from=assets /root/frappe-bench/sites /usr/share/nginx/html
