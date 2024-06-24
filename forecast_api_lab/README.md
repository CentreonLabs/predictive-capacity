![coverage](assets/coverage.svg)

# FastAPI Backend

## Development environment

The backend of predictive capacity is written in Python 3.10 and uses poetry for dependency management. To set up the development environment, follow these steps:

1. Install poetry: https://python-poetry.org/docs/#installation
2. Not necessary, but recommended: create a virtual environment: `python3.10 -m venv .venv`
3. Install dependencies: `poetry install`
4. Test the installation: `poetry run pytest`

Here are few useful commands:

* To update all dependencies, run `poetry update`.
* To add new dependencies, run `poetry add my-new-package`.
* To add new dependencies only useful for development (tests, formatting, ...), run `poetry add --dev my-new-package`.
* To push new changes, don't forget to update the version number in `pyproject.toml` which you can do with `poetry version patch` (or `minor` or `major`).

## How to run the application locally

You can run the application with the following command:

```bash
python -m uvicorn  predictive_capacity.api:app  --host  0.0.0.0 --port 7000
```