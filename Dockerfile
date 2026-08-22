FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade "setuptools>=78.1.1" \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && rm -f /usr/local/lib/python3.13/ensurepip/_bundled/setuptools-*.whl \
    && adduser -D -u 10001 appuser

COPY pcradio_mcp ./pcradio_mcp

USER appuser
EXPOSE 8080
CMD ["python", "-m", "pcradio_mcp.server"]