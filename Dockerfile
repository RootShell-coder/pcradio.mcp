FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY pcradio_mcp ./pcradio_mcp

RUN useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 8080
CMD ["python", "-m", "pcradio_mcp.server"]

