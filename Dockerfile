FROM python:3.12-slim

WORKDIR /app

COPY calculator_mcp.py /app/calculator_mcp.py

ENTRYPOINT ["python", "/app/calculator_mcp.py"]
