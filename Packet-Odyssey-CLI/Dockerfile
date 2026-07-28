FROM python:3.12-alpine3.21
WORKDIR /app
COPY src ./src
ENV PYTHONPATH=/app/src PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "packet_odyssey"]
CMD ["--help"]
