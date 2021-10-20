FROM python:3.9-slim-buster

ENV PYTHONUNBUFFERED 1

RUN useradd -ms /bin/bash frappe

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
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
  && rm -rf /var/lib/apt/lists/*

# Setup docker-entrypoint
RUN git clone --depth 1 -b develop https://github.com/frappe/frappe_docker /tmp/frappe_docker \
  && cd /tmp/frappe_docker \
  && cp build/common/worker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh \
  && ln -s /usr/local/bin/docker-entrypoint.sh / \
  && mkdir -p /home/frappe/frappe-bench/commands \
  && cp build/common/commands/* /home/frappe/frappe-bench/commands \
  && mkdir /opt/frappe \
  && cp build/common/common_site_config.json.template /opt/frappe/common_site_config.json.template \
  && cp build/common/worker/install_app.sh /usr/local/bin/install_app \
  && cp build/common/worker/bench /usr/local/bin/bench \
  && cp build/common/worker/healthcheck.sh /usr/local/bin/healthcheck.sh \
  && chown -R frappe:frappe /home/frappe

# Install wkhtmltopdf
ENV WKHTMLTOPDF_VERSION 0.12.6-1
RUN if [ "$(uname -m)" = "aarch64" ]; then export ARCH=arm64; fi \
  && if [ "$(uname -m)" = "x86_64" ]; then export ARCH=amd64; fi \
  && downloaded_file=wkhtmltox_$WKHTMLTOPDF_VERSION.buster_${ARCH}.deb \
  && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/$WKHTMLTOPDF_VERSION/$downloaded_file \
  && dpkg -i $downloaded_file \
  && rm $downloaded_file


USER frappe
WORKDIR /home/frappe/frappe-bench

RUN mkdir apps logs sites /home/frappe/backups

# Setup python environment
RUN python -m venv env
RUN env/bin/pip install --no-cache-dir wheel gevent

# Install nvm with node
ENV NODE_VERSION 14.18.1
ENV NVM_DIR /home/frappe/.nvm
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin/:$PATH
RUN wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash \
  && . $NVM_DIR/nvm.sh \
  && nvm install $NODE_VERSION \
  && rm -rf $NVM_DIR/.cache

# Install Frappe
ARG FRAPPE_VERSION
RUN git clone --depth 1 -b $FRAPPE_VERSION https://github.com/frappe/frappe apps/frappe \
  && env/bin/pip install --no-cache-dir -e apps/frappe

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
