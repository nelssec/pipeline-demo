# PHP-FPM service for the PHP2Shell demo (CVE-2026-109618 / CVE-2026-109619).
#
# PHP comes from Ubuntu packages, not the official php: image. The official image compiles
# PHP from source, so neither QScanner nor Container Security inventories the PHP version
# and PHP2Shell is never reported. Ubuntu fixed PHP2Shell in 8.3.6-0ubuntu0.24.04.13
# (USN-8948-1, QID 6877310); .12 is the last vulnerable build. Superseded builds are no
# longer in the archive pool, so the .debs come from Launchpad.
#
# The PHP2Shell remediation workflow rewrites PHP_PKG_VERSION; keep it on one line.
FROM ubuntu:24.04
ARG PHP_PKG_VERSION=8.3.6-0ubuntu0.24.04.12
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl; \
    arch="$(dpkg --print-architecture)"; \
    mkdir /tmp/php; cd /tmp/php; \
    for p in common opcache readline cli fpm; do \
      curl -fsSL --retry 6 --retry-all-errors --retry-delay 10 -o "php8.3-$p.deb" "https://launchpad.net/ubuntu/+archive/primary/+files/php8.3-${p}_${PHP_PKG_VERSION}_${arch}.deb"; \
    done; \
    apt-get install -y --no-install-recommends --allow-downgrades ./*.deb; \
    apt-mark hold php8.3-common php8.3-opcache php8.3-readline php8.3-cli php8.3-fpm; \
    rm -rf /tmp/php /var/lib/apt/lists/*; \
    sed -i 's|^listen = .*|listen = 9000|' /etc/php/8.3/fpm/pool.d/www.conf; \
    mkdir -p /run/php
WORKDIR /var/www/html
COPY public/ ./
EXPOSE 9000
CMD ["php-fpm8.3", "-F"]
