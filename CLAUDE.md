# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

skill-installer is a Python project for installing and managing Claude Code skills.

## Development Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies (when pyproject.toml exists)
pip install -e ".[dev]"
```

## Commands

```bash
# Run tests
pytest

# Run single test
pytest tests/test_file.py::test_function -v

# Type checking
mypy src/

# Linting
ruff check .

# Format code
ruff format .
```

## Project Structure

This is a new project. As it develops, structure will be added here.
