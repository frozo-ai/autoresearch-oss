# Contributing to autoresearch-oss

Thanks for your interest in contributing! Here's how to get started.

## Quick Setup

```bash
git clone https://github.com/frozo-ai/autoresearch-oss.git
cd autoresearch-oss
pip install -e ".[dev]"
```

## Development

```bash
# Run tests
pytest runner/tests/ cli/tests/ -v

# Lint
ruff check .

# Format
ruff format .
```

## How to Contribute

### Bug Reports
Open an issue with:
- What you expected
- What happened
- Steps to reproduce
- Your OS, Python version, and provider (Anthropic/OpenAI/Gemini)

### Feature Requests
Open an issue describing the use case and why it matters.

### Pull Requests
1. Fork the repo
2. Create a branch: `git checkout -b my-feature`
3. Make your changes
4. Add tests for new functionality
5. Run `pytest` to make sure everything passes
6. Submit a PR

### Areas We Need Help
- New eval templates (submit to `templates/`)
- Provider support (new LLM providers)
- Bug fixes in the ratchet loop
- Documentation improvements
- CLI UX improvements

## Code Style
- Python 3.10+
- Ruff for linting and formatting
- Line length: 100 chars
- Type hints encouraged

## License
By contributing, you agree that your contributions will be licensed under the MIT License.
