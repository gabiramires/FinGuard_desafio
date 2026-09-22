IMAGE ?= finguard:latest
INPUT ?= data/reclamacoes.csv
PROVIDER ?=
MODEL ?=
LIMIT ?=
ARGS ?=

PROVIDER_ARG = $(if $(PROVIDER),--provider $(PROVIDER),)
MODEL_ARG = $(if $(MODEL),--model $(MODEL),)

DOCKER_RUN = docker compose run --rm finguard

GOLD ?= data/gold/labels-ai-draft-v2.csv

.PHONY: help build rebuild run run-nivel1 run-nivel2 run-nivel1-limit run-nivel2-limit benchmark-nivel1 benchmark-nivel2 shell clean-reports

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

build: ## Constrói a imagem Docker
	docker compose build

rebuild: ## Reconstrói a imagem sem cache
	docker compose build --no-cache

run: run-nivel1 ## Alias para run-nivel1

run-nivel1: ## Executa nível 1 (classificador)
	$(DOCKER_RUN) --nivel 1 --input $(INPUT) $(PROVIDER_ARG) $(MODEL_ARG) $(if $(LIMIT),--limit $(LIMIT),) $(ARGS)

run-nivel2: ## Executa nível 2 (orquestrador multi-agente)
	$(DOCKER_RUN) --nivel 2 --input $(INPUT) $(PROVIDER_ARG) $(MODEL_ARG) $(if $(LIMIT),--limit $(LIMIT),) $(ARGS)

run-nivel1-limit: ## Executa nível 1 com LIMIT=5 (ex.: make run-nivel1-limit LIMIT=5)
	$(MAKE) run-nivel1 LIMIT=$(or $(LIMIT),5)

run-nivel2-limit: ## Executa nível 2 com LIMIT=5 (ex.: make run-nivel2-limit LIMIT=5)
	$(MAKE) run-nivel2 LIMIT=$(or $(LIMIT),5)

benchmark-nivel1: ## Benchmark nível 1 com gold (LIMIT/MODEL opcionais)
	$(DOCKER_RUN) --nivel 1 --input $(INPUT) $(PROVIDER_ARG) $(MODEL_ARG) --benchmark --gold $(GOLD) $(if $(LIMIT),--limit $(LIMIT),) $(ARGS)

benchmark-nivel2: ## Benchmark nível 2 com gold (LIMIT/MODEL opcionais)
	$(DOCKER_RUN) --nivel 2 --input $(INPUT) $(PROVIDER_ARG) $(MODEL_ARG) --benchmark --gold $(GOLD) $(if $(LIMIT),--limit $(LIMIT),) $(ARGS)

shell: ## Abre shell interativo no container
	docker compose run --rm --entrypoint /bin/bash finguard

clean-reports: ## Remove arquivos gerados em reports/
	rm -f reports/*.json reports/*.csv reports/*.html reports/*.md reports/*.jsonl
