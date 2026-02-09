# Makefile for building and saving app_env Docker image

IMAGE_NAME = app_env
IMAGE_TAG = latest
IMAGE_FULL = $(IMAGE_NAME):$(IMAGE_TAG)
OUTPUT_FILE = app_env.tar.gz
DOCKERFILE = server/Dockerfile.app_env
BUILD_CONTEXT = server

.PHONY: build-env
build-env:
	@echo "Building Docker image $(IMAGE_FULL)..."
	docker build --platform linux/amd64 -t $(IMAGE_FULL) -f $(DOCKERFILE) $(BUILD_CONTEXT)
	@echo "Saving Docker image to $(OUTPUT_FILE)..."
	docker save $(IMAGE_FULL) | gzip > $(OUTPUT_FILE)
	@echo "Docker image saved to $(OUTPUT_FILE)"

.PHONY: package
package:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Creating server package (excluding venv and __pycache__)..."
	tar --exclude='server/.venv' --exclude='server/__pycache__' -czf server.tar.gz server/
	@echo "Server package created as server.tar.gz"

.PHONY: run
run:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Frontend build complete!"
	@echo "Starting server in Docker app_env..."
	docker run --rm -it \
		-p 8080:8080 \
		-v $(PWD)/server:/opt/code \
		-v $(PWD)/frontend/dist:/opt/code/app/frontend/dist \
		-w /opt/code \
		$(IMAGE_FULL) \
		python main.py
