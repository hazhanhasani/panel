# BluePanel development Makefile

PYTHON_VERSION=3.14
VENV_DIR=.venv

.PHONY: install_uv
install_uv:
	@if ! uv --help >/dev/null 2>&1; then \
		echo "uv not found. Installing..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "uv installed. Ensure ~/.cargo/bin is in your PATH."; \
	else \
		echo "uv is already installed."; \
	fi

.PHONY: requirements
requirements:
	@uv sync

.PHONY: requirements-dev
requirements-dev:
	@uv sync --group dev

.PHONY: check-nvm
check-nvm:
	@if ! command -v nvm > /dev/null 2>&1; then \
		echo "nvm not found. Installing..."; \
		curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash || { \
			echo "Failed to install nvm. Please install it manually."; \
			exit 1; \
		}; \
		export NVM_DIR="$$HOME/.nvm"; \
		[ -s "$$NVM_DIR/nvm.sh" ] && . "$$NVM_DIR/nvm.sh"; \
		[ -s "$$NVM_DIR/bash_completion" ] && . "$$NVM_DIR/bash_completion"; \
		echo "nvm installed. Version: `nvm --version`"; \
	else \
		echo "nvm is already installed. Version: `nvm --version`"; \
	fi

.PHONY: check-nodejs
check-nodejs: check-nvm
	@if ! node -v > /dev/null 2>&1; then \
		echo "nodejs not found. Installing..."; \
		nvm install 22 || { \
			echo "Failed to install nodejs. Please install it manually."; \
			exit 1; \
		}; \
	else \
		echo "nodejs is already installed."; \
	fi

.PHONY: check-bun
check-bun: check-nodejs
	@if ! bun --version > /dev/null 2>&1; then \
		echo "bun not found. Installing..."; \
		curl -fsSL https://bun.sh/install | bash || { \
			echo "Failed to install bun. Please install it manually."; \
			exit 1; \
		}; \
	else \
		echo "bun is already installed."; \
	fi

.PHONY: install-front
install-front: check-bun
	@cd dashboard && bun install

.PHONY: run-migration
run-migration:
	@uv run alembic upgrade head

.PHONY: check-migrations
check-migrations:
	@uv run alembic check

# Run BluePanel
.PHONY: run
run:
	@uv run main.py

# Run BluePanel CLI
.PHONY: run-cli
run-cli:
	@uv run bluepanel-cli.py

.PHONY: test
test:
	@uv run pytest tests/

.PHONY: test-whatch
test-whatch:
	@uv run ptw

# Run BluePanel with watchfiles
.PHONY: run-watch
run-watch:
	@echo "Running BluePanel with watchfiles..."
	@uv run watchfiles --filter python "uv run main.py" .

.PHONY: gen-api
gen-api:
	@uv run python scripts/export_openapi.py --gen-client

.PHONY: check
check:
	@uv run ruff check .

.PHONY: format
format:
	@uv run ruff format .

.PHONY: clean
clean:
	@rm -rf $(VENV_DIR)
	@echo "Virtual environment removed."

.PHONY: setup
setup: install_uv requirements

.PHONY: setup-test
setup-test: install_uv requirements-dev

.PHONY: fformat
fformat:
	@cd dashboard && bun run prettier . --write
