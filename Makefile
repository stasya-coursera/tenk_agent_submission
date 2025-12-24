.PHONY: setup run-docker test run-index install-dev dev

# Default Python version
PYTHON := python3.11
VENV_DIR := .venv

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

setup: ## Create virtual environment and install dependencies
	@echo "$(YELLOW)🔧 Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(YELLOW)📦 Installing dependencies...$(NC)"
	$(VENV_DIR)/bin/pip install --upgrade pip
	$(VENV_DIR)/bin/pip install -e .
	@echo "$(GREEN)✅ Setup complete! Activate with: source $(VENV_DIR)/bin/activate$(NC)"

run-docker: ## Start Docker containers
	@echo "$(YELLOW)🐳 Starting Docker containers...$(NC)"
	docker-compose up --build

test: ## Run test questions
	@echo "$(YELLOW)🧪 Running test questions...$(NC)"
	@if [ ! -f "$(VENV_DIR)/bin/activate" ]; then \
		echo "$(RED)❌ Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	$(VENV_DIR)/bin/python test_cli_questions.py

install-dev: ## Install development dependencies
	@echo "$(YELLOW)📦 Installing development dependencies...$(NC)"
	@if [ ! -f "$(VENV_DIR)/bin/activate" ]; then \
		echo "$(RED)❌ Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	$(VENV_DIR)/bin/python -m pip install -e ".[dev]"
	@echo "$(GREEN)✅ Development dependencies installed$(NC)"

dev: ## Start LangGraph development server
	@echo "$(YELLOW)🚀 Starting LangGraph dev server...$(NC)"
	@if [ ! -f "$(VENV_DIR)/bin/activate" ]; then \
		echo "$(RED)❌ Virtual environment not found. Run 'make setup' first.$(NC)"; \
		exit 1; \
	fi
	$(VENV_DIR)/bin/langgraph dev --allow-blocking

