FROM python:3.9-slim-bullseye


RUN apt-get update \
  && apt-get install --no-install-recommends -y wget gnupg \
  && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
  && apt-get update \
  && apt-get install -y google-chrome-unstable --no-install-recommends \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash user
USER user
WORKDIR /home/user

ENV VIRTUAL_ENV venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH $VIRTUAL_ENV/bin:$PATH

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY main.py .

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
