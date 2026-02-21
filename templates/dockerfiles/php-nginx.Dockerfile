# PHP + Nginx Dockerfile (Laravel / Symfony / plain PHP)
# Агент: подставь значения переменных перед использованием.
# ${PHP_VERSION} — версия PHP (по умолчанию 8.3)
# ${DOC_ROOT} — document root (Laravel: /app/public, Symfony: /app/public, plain: /app)

FROM php:${PHP_VERSION}-fpm-alpine

# Системные зависимости + расширения PHP
RUN apk add --no-cache nginx supervisor curl \
    && docker-php-ext-install pdo pdo_mysql opcache

# Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /app
COPY composer.json composer.lock* ./
RUN composer install --no-dev --optimize-autoloader --no-scripts

COPY . .
RUN composer dump-autoload --optimize

# Nginx конфиг
RUN echo 'server { \
    listen 80; \
    root ${DOC_ROOT}; \
    index index.php index.html; \
    location / { try_files $uri $uri/ /index.php?$query_string; } \
    location ~ \.php$ { \
        fastcgi_pass 127.0.0.1:9000; \
        fastcgi_index index.php; \
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name; \
        include fastcgi_params; \
    } \
}' > /etc/nginx/http.d/default.conf

# Supervisor для nginx + php-fpm
RUN echo -e '[supervisord]\nnodaemon=true\n[program:nginx]\ncommand=nginx -g "daemon off;"\n[program:php-fpm]\ncommand=php-fpm -F' > /etc/supervisord.conf

# Права для Laravel/Symfony
RUN chown -R www-data:www-data /app/storage /app/bootstrap/cache 2>/dev/null || true

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost/ || exit 1
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
