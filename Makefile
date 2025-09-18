###############################
#		CONSTANTS
###############################
VERSION 	?= main
GIT_COMMIT  ?= $(shell git rev-list -1 HEAD)
CONTAINER_IMAGE ?= ghcr.io/kedify/keda-prophet
DEV_LOG_LVL ?= info
# DEV_LOG_LVL ?= trace
ARCH ?= $(shell uname -m)
ifeq ($(ARCH), x86_64)
	ARCH=amd64
endif


###############################
#		TARGETS
###############################
all: help

##@ Build

.PHONY: build-image
build-image: ## Builds the container image for current arch.
	@$(call say,Build container image $(CONTAINER_IMAGE))
	docker build . -t $(CONTAINER_IMAGE):$(VERSION) --build-arg VERSION=$(VERSION) --build-arg GIT_COMMIT=$(GIT_COMMIT)

.PHONY: build-image-multiarch
build-image-multiarch: ## Builds the container image for amd and arm arch and pushes them to container registry.
	@$(call say,Build container image $(CONTAINER_IMAGE))
	docker buildx build . --push --platform linux/amd64,linux/arm64 -t $(CONTAINER_IMAGE):$(VERSION) --build-arg VERSION=$(VERSION) --build-arg GIT_COMMIT=$(GIT_COMMIT)

##@ General
.PHONY: run-dev
run-dev: ## Runs the REST api
	@$(call say,Starting REST api)
	python3 -m venv venv && \
	source venv/bin/activate && \
	python3 -m uvicorn app.main:app --log-level $(DEV_LOG_LVL) --reload

.PHONY: run-dev-fill-db
run-dev-fill-db: ## Runs the REST api with pre-filled database
	@$(call say,Starting REST api)
	python3 -m venv venv && \
	source venv/bin/activate && \
	cp data/sample-db.sqlite data/sample-db.sqlite_cpy && \
	DB_FILE=data/sample-db.sqlite_cpy python3 -m uvicorn app.main:app --log-level $(DEV_LOG_LVL) --reload

.PHONY: run-image
run-image: ## Runs the REST api from ghcr.io/kedify/keda-prophet:main container image
	@$(call say,Starting REST api)
	docker run -ti -p8000:8000 $(CONTAINER_IMAGE):$(VERSION)

.PHONY: run-k3d
run-k3d: build-image ## Creates k3d cluster w/ KEDA Prophet and some test data
	@$(call say,Creating k3d cluster prophet)
	-k3d cluster delete prophet && sleep 1
	k3d cluster create prophet -p "8000:31111@server:0"
	@$(call say,Importing image)
	k3d image import -c prophet ghcr.io/kedify/keda-prophet:main
	@$(call say,Installing helmchart w/ sample DB)
	helm upgrade -i foo ./helmchart/keda-prophet \
		--set image.tag=main \
		--set image.pullPolicy=Never \
		--set service.type=NodePort \
		--set service.nodePort=31111 \
		--set fullnameOverride=keda-prophet \
		--set settings.storage.dbFile=/app/data/sample-db.sqlite
	@$(call say,Opening browser)
	kubectl rollout status --timeout=600s deploy/keda-prophet
	@open http://localhost:8000
	@echo "\nContinue w/:\n  - curl -s localhost:8000/models | jq\nretraining them:\n  - curl -s localhost:8000/models/{name}/retrain\nExplore them:\n  - open http://localhost:8000/models/{name}/graph"
	@echo "\n\nTo start the data feeder & retrainer:\n  - kubectl apply -f example/\n🚀"

.PHONY: deploy-k8s
deploy-k8s: ## Deploys the KEDA Prophet to current k8s context
	@$(call say,Deploying to k8s)
	kubectl apply -f k8s/deployment.yaml
	@echo "\ncontinue with: \nkubectl port-forward svc/keda-prophet 8000:8000\nmake check-model"

.PHONY: check-model
check-model: ## Prepares a model and open its graph with predictions
	@$(call say,Demoing the a model)
	@$(call say,Feeding the DB with sample data..)
	curl http://127.0.0.1:8000/models/foo/testData
	@$(call say,Fitting the model to the data - training)
	curl http://127.0.0.1:8000/models/foo/retrain
	@$(call say,Opening the graph with predictions)
	open 'http://127.0.0.1:8000/models/foo/graph?periods=200&hoursAgo=120'

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)


###############################
#		HELPERS
###############################

ifndef NO_COLOR
YELLOW=\033[0;33m
# no color
NC=\033[0m
endif

define say
echo "\n$(shell echo "$1  " | sed s/./=/g)\n $(YELLOW)$1$(NC)\n$(shell echo "$1  " | sed s/./=/g)"
endef
