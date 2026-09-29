FROM python:3.12-slim

WORKDIR /workspace
COPY pyproject.toml README.md ./
COPY app ./app
COPY evals ./evals
COPY data ./data

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["research-agent"]
