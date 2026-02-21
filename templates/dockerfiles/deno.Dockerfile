# Deno Dockerfile
# Агент: подставь значения переменных перед использованием.
# ${DENO_VERSION} — версия Deno (по умолчанию latest)
# ${PORT} — порт приложения (по умолчанию 8000)
# ${ENTRY_POINT} — главный файл (main.ts / src/main.ts / mod.ts)
# ${PERMISSIONS} — флаги разрешений (--allow-net --allow-read --allow-env)

FROM denoland/deno:${DENO_VERSION}
WORKDIR /app
COPY deno.json* deno.lock* ./
RUN deno install || true
COPY . .
RUN deno cache ${ENTRY_POINT}
EXPOSE ${PORT}
USER deno
CMD ["deno", "run", ${PERMISSIONS}, "${ENTRY_POINT}"]
