# Python Dockerfile (FastAPI, Flask, Django, aiohttp, Tornado)
# Агент: подставь значения переменных перед использованием.
# ${PYTHON_VERSION} — версия Python (по умолчанию 3.12)
# ${PORT} — порт приложения (по умолчанию 8000)
# ${START_CMD} — команда запуска:
#   FastAPI → uvicorn main:app --host 0.0.0.0 --port ${PORT}
#   Flask → gunicorn app:app -w 4 -b 0.0.0.0:${PORT}
#   Django → gunicorn config.wsgi:application -w 4 -b 0.0.0.0:${PORT}
#   aiohttp → python main.py
#   Tornado → python main.py

FROM python:${PYTHON_VERSION}-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE ${PORT}
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/')" || exit 1
CMD ${START_CMD}
