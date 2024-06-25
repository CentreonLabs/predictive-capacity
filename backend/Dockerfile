FROM python:3.10

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y groff less && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.4.2

# System deps:
RUN pip install "poetry==$POETRY_VERSION"

# Copy only requirements to cache them in docker layer
WORKDIR /code
COPY poetry.lock pyproject.toml /code/

# Project initialization:
RUN poetry install --no-dev --no-interaction --no-ansi

# Creating folders, and files for a project:
COPY predictive_capacity /code/predictive_capacity

# Exposing port:
EXPOSE 7000

# Running entrypoint:
ENTRYPOINT ["poetry", "run", "uvicorn", "predictive_capacity.api:app", "--host", "0.0.0.0", "--port", "7000"]
