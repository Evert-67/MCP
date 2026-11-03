FROM python:3.12-slim
WORKDIR /opt/codepug
RUN useradd --system --uid 10001 --create-home codepug
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dashboard/ ./dashboard/
USER 10001:10001
EXPOSE 8768
CMD ["uvicorn", "dashboard.app:app", "--host", "0.0.0.0", "--port", "8768", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
