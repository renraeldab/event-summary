# Event Summary

A data pipeline that automatically crawls information about a specific event or topic and generates a structured summary webpage.

## Asynchronous Architecture

- **Producer-Consumer Pattern**
    - Decouple data acquisition from processing
    - **Producers**: `Retriever` instances fetch webpages and enqueue URLs into queues
    - **Consumers**: `Processor` instances consume URLs from queues for batch processing
    - Configurable consumption batch size

- **Dual-Queue**
    - Enable independent scaling of entity extraction and theme generation workloads
    - Progress tracking via tqdm bars synchronized with queue operations

- **Controlled Concurrency**
    - Retriever fetching concurrency
    - Processor parallelism
    - LLM concurrency

## Project Structure

```
event-summary/
├── pyproject.toml
├── uv.lock
├── requirements.txt
├── .gitignore
├── .env.example
├── LICENSE
├── README.md
├── tests/
│   ├── ...
├── data/
│   ├── ...
├── data_pipeline/
│   ├── __init__.py
│   ├── __main__.py
│   ├── models.py
│   ├── crawling/
│   │   ├── __init__.py
│   │   └── ...
│   └── processing/
│       ├── __init__.py
│       └── ...
└── html_generator/
    ├── __init__.py
    ├── __main__.py
    └── template.html
```

## Environment

### uv (recommended)

#### Setup

```bash
# Create a virtual environment and install dependencies
uv sync

# Activate the environment (if needed)
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

#### Add Dependencies

```bash
# Add dependencies and update uv files
uv add xxx

# Update requirements.txt
uv pip freeze > requirements.txt
```

#### Update

```bash
# Update from uv files
uv sync
# or manually update from changes in requirements.txt
uv add xxx
```

### conda and pip

#### Setup

```bash
# Create a new conda environment
conda create -n event-summary python=3.12

# Activate the environment
conda activate event-summary

# Install dependencies from requirements.txt using pip
pip install -r requirements.txt
```

#### Add Dependencies

```bash
# Add dependencies
pip install xxx

# Update requirements.txt
pip freeze > requirements.txt
```

#### Update

```bash
# Install updated dependencies
pip install -r requirements.txt
```

## Usage

### Steps

1. Setup the environment.
2. Copy `.env.example` as `.env`, and change the configuration.
3. Move to the project directory.
4. Run `python -m data_pipeline "a certain topic or event"` to collect data.
5. Run `python -m html_generator` to generate an HTML file.

### Configuration

...