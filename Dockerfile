FROM python:3.9-alpine

RUN apk add --no-cache \
    udev \
    ttf-freefont \
    chromium \
    && rm -rf /usr/include \
    && rm -rf /var/cache/apk/* /usr/share/man /tmp/*

ENV CHROME_BIN="/usr/bin/chromium-browser"

COPY . /auther
WORKDIR /auther

RUN pip install -r requirements.txt

RUN pip install .

ENTRYPOINT [ "auther" ]