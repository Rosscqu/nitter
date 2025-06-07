FROM alpine:3.18 AS nim
LABEL maintainer="setenforce@protonmail.com"

RUN apk --no-cache add libsass-dev pcre gcc git libc-dev "nim=1.6.14-r0" "nimble=0.13.1-r2"

WORKDIR /src/nitter

COPY nitter.nimble .
RUN nimble install -y --depsOnly

COPY . .
RUN nimble build -d:danger -d:lto -d:strip \
    && nimble scss \
    && nimble md

FROM alpine:3.18 AS overmind
RUN apk --no-cache add go
RUN go install github.com/DarthSim/overmind/v2@latest

FROM alpine:3.18
WORKDIR /src/
# RUN apk --no-cache add pcre ca-certificates openssl1.1-compat
RUN apk --no-cache add pcre ca-certificates openssl1.1-compat bash redis tmux nginx python3 py3-pip
RUN pip install requests passlib beautifulsoup4
COPY --from=nim /src/nitter/nitter ./
COPY --from=nim /src/nitter/nitter.example.conf ./nitter.conf
COPY --from=nim /src/nitter/public ./public
# self-contained bits start
COPY --from=overmind /root/go/bin/overmind ./
COPY scripts/ ./scripts/
COPY scripts/assets/redis.conf ./redis.conf
COPY scripts/assets/nginx.conf /etc/nginx/nginx.conf
COPY nitter-data/guest_accounts.json  ../nitter-data/guest_accounts.json
RUN mkdir -p /etc/nginx/conf.d
# self-contained bits end
EXPOSE 8081
# RUN adduser -h /src/ -D -s /bin/sh nitter
# USER nitter
CMD ["bash", "-c", "/src/scripts/dump_env_and_procfile.sh && /src/overmind s"]
