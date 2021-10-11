ARG FRAPPE_VERSION
FROM python:3.9-slim-buster

ARG ARCH=amd64
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
  apt-get install --no-install-recommends -y \
  # for frappe framework
  git \
  mariadb-client \
  gettext-base \
  wget \
  wait-for-it \
  # for PDF
  libjpeg62-turbo \
  libx11-6 \
  libxcb1 \
  libxext6 \
  libxrender1 \
  libssl-dev \
  fonts-cantarell \
  xfonts-75dpi \
  xfonts-base \
  libxml2 \
  libffi-dev \
  libjpeg-dev \
  zlib1g-dev \
  # For psycopg2
  libpq-dev \
  # For arm64 python wheel builds
  && if [ "$(uname -m)" = "aarch64" ]; then apt-get install --no-install-recommends -y gcc g++; fi \
  # Detect arch, download and install wkhtmltox
  && if [ "$(uname -m)" = "aarch64" ]; then export ARCH=arm64; fi \
  && if [ "$(uname -m)" = "x86_64" ]; then export ARCH=amd64; fi \
  && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.buster_${ARCH}.deb \
  && dpkg -i wkhtmltox_0.12.6-1.buster_${ARCH}.deb \
  && rm wkhtmltox_0.12.6-1.buster_${ARCH}.deb \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash frappe
WORKDIR /home/frappe/frappe-bench

# Setup docker-entrypoint
RUN git clone --depth 1 -b develop https://github.com/frappe/frappe_docker ~/frappe_docker \
  && cd ~/frappe_docker \
  && cp build/common/worker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh \
  && ln -s /usr/local/bin/docker-entrypoint.sh / \
  && mkdir -p /home/frappe/frappe-bench/commands \
  && cp build/common/commands/* /home/frappe/frappe-bench/commands \
  && mkdir /opt/frappe \
  && cp build/common/common_site_config.json.template /opt/frappe/common_site_config.json.template \
  && cp build/common/worker/install_app.sh /usr/local/bin/install_app \
  && cp build/common/worker/bench /usr/local/bin/bench \
  && cp build/common/worker/healthcheck.sh /usr/local/bin/healthcheck.sh \
  && rm -rf ~/frappe_docker \
  && chown -R frappe:frappe /home/frappe

USER frappe

# Install nvm with node
ENV NODE_VERSION=14.18.0
ENV NVM_DIR=/home/frappe/.nvm
ENV PATH="/home/frappe/.nvm/versions/node/v${NODE_VERSION}/bin/:${PATH}"
RUN wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash \
  && . "$NVM_DIR/nvm.sh" \
  && nvm install ${NODE_VERSION} \
  && nvm alias default v${NODE_VERSION} \
  && nvm use default \
  && rm -rf ~/.nvm/.cache

# Setup python environment
ARG FRAPPE_VERSION
RUN mkdir apps logs sites /home/frappe/backups \
  && python -m venv env \
  && . env/bin/activate \
  && pip install --no-cache-dir -U pip wheel gevent \
  && git clone --depth 1 -b ${FRAPPE_VERSION} https://github.com/frappe/frappe apps/frappe \
  && pip install --no-cache-dir -e apps/frappe

# Install Comfort
COPY --chown=frappe . apps/comfort
RUN env/bin/pip install --no-cache-dir -e apps/comfort

# Overwrite connection check commands
COPY --chown=frappe docker/scripts/check_connection.py docker/scripts/doctor.py /home/frappe/frappe-bench/commands/

# Use sites volume as working directory
WORKDIR /home/frappe/frappe-bench/sites

VOLUME [ "/home/frappe/frappe-bench/sites", "/home/frappe/backups", "/home/frappe/frappe-bench/logs" ]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]
