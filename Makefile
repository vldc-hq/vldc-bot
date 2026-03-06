SHELL = /bin/bash

.DEFAULT_GOAL := help
.PHONY: go_run go_test go_fmt go_lint go_cover migrate-up migrate-down migrate-status migrate-data docker-build

GOOSE_VERSION ?= v3.26.0
SQLITE_DB_PATH ?= bot.db

go_run: ## Run Go bot
	go run ./cmd/nyanbot

go_test: ## Run Go tests
	go test ./...

go_fmt: ## Format Go code
	gofmt -w ./cmd ./internal

go_lint: ## Run Go linters locally
	go install mvdan.cc/gofumpt@latest
	go install honnef.co/go/tools/cmd/staticcheck@latest
	go install golang.org/x/vuln/cmd/govulncheck@latest
	gofumpt -l ./cmd ./internal
	staticcheck ./...
	govulncheck ./...

go_cover: ## Run Go tests with coverage profile
	go test -coverprofile=coverage.out ./...

migrate-up: ## Apply SQLite migrations (goose)
	go run github.com/pressly/goose/v3/cmd/goose@$(GOOSE_VERSION) -dir db/migrations sqlite3 "$(SQLITE_DB_PATH)" up

migrate-down: ## Roll back one SQLite migration (goose)
	go run github.com/pressly/goose/v3/cmd/goose@$(GOOSE_VERSION) -dir db/migrations sqlite3 "$(SQLITE_DB_PATH)" down

migrate-status: ## Show SQLite migration status (goose)
	go run github.com/pressly/goose/v3/cmd/goose@$(GOOSE_VERSION) -dir db/migrations sqlite3 "$(SQLITE_DB_PATH)" status

migrate-data: ## Copy data between SQLite files
	SOURCE_SQLITE_DB_PATH="$(SOURCE_SQLITE_DB_PATH)" TARGET_SQLITE_DB_PATH="$(TARGET_SQLITE_DB_PATH)" go run ./cmd/nyan-migrate

docker-build: ## Build Go runtime container
	docker build -f Dockerfile.nyan-go -t vldc-nyan-go:local .

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
