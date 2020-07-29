FROM alpine

RUN apk add -U rsync \
    && rm -rf /var/cache/apk/*

COPY rsyncd.conf /etc/

VOLUME /share
EXPOSE 873

CMD rsync --daemon --no-detach --log-file /dev/stdout