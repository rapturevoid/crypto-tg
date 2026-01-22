FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN apt-get update && apt-get install -y \
    build-essential libgmp3-dev libmpfr-dev

RUN uv sync 


COPY . .

CMD ["uv", "run", "--env-file=.env", "main.py"]
