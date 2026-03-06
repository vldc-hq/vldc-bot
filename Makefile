SHELL = /bin/bash

.DEFAULT_GOAL := help
.PHONY: build test lint format run docker-build docker-up docker-down help

## Go targets

build:  ## Build the bot binary
	go build -o bin/vldc-bot ./cmd/bot

run:  ## Run the bot locally
	go run ./cmd/bot

test:  ## Run all tests
	go test -race -count=1 ./...

test-cover:  ## Run tests with coverage report
	go test -race -coverprofile=coverage.out -covermode=atomic ./...
	go tool cover -html=coverage.out -o coverage.html

lint:  ## Run golangci-lint
	golangci-lint run ./...

format:  ## Format code with goimports
	goimports -w .

tidy:  ## Run go mod tidy
	go mod tidy

## Docker targets

docker-build:  ## Build Docker image
	docker build -t vldc-bot .

docker-up:  ## Run with docker-compose
	docker-compose up -d && docker-compose logs -f --tail=10

docker-down:  ## Stop docker-compose
	docker-compose down

## Help

help: ## Show help message
	@IFS=$$'\n' ; \
	help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/:/'`); \
	printf "%s\n\n" "Usage: make [task]"; \
	printf "%-20s %s\n" "task" "help" ; \
	printf "%-20s %s\n" "------" "----" ; \
	for help_line in $${help_lines[@]}; do \
		IFS=$$':' ; \
		help_split=($$help_line) ; \
		help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		printf '\033[36m'; \
		printf "%-20s %s" $$help_command ; \
		printf '\033[0m'; \
		printf "%s\n" $$help_info; \
	done
