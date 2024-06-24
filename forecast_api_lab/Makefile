IMAGE_NAME = 333885346763.dkr.ecr.eu-west-1.amazonaws.com/internal-centreon-saas-forecast-api-ml-aiops
CONTAINER_NAME = centreon-saas-forecast-api-ml-aiops
VERSION=$(shell poetry version -s)

.PHONY: format build run deploy update coverage

all: update format test

update:
	poetry update
	poetry lock

format: 
	isort .
	black .

test: format 
	poetry run coverage run -m pytest
	rm assets/coverage.svg || true
	poetry run coverage-badge -o assets/coverage.svg
	poetry run coverage report -m

build:
	docker build -t $(IMAGE_NAME):$(VERSION) --pull .
	docker tag $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest
	docker images --filter "reference=$(IMAGE_NAME)" --filter "before=$(IMAGE_NAME):latest" -q | xargs docker rmi -f || true

run: build
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true
	docker run --name $(CONTAINER_NAME) -d -p 8000:8000 -v ~/.aws:/root/.aws --env-file=.env $(IMAGE_NAME):$(VERSION)
	docker logs -f $(CONTAINER_NAME)

deploy: update test build
	aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin $(IMAGE_NAME)
	docker push $(IMAGE_NAME):$(VERSION)
	docker push $(IMAGE_NAME):latest
	ssh -i ~/.ssh/id_rsa_centreon droussel@10.32.3.146 "sudo /srv/upgrade.sh && sudo docker image prune -f" 
	ssh -i ~/.ssh/id_rsa_centreon droussel@10.32.5.123 "sudo /srv/upgrade.sh && sudo docker image prune -f"

