---
name: autoresearch
version: 0.2.0
description: Autonomous experiment loop runner — optimize any file overnight with AI
binary: ars
install: pip install autoresearch-cli
provider_agnostic: true
supported_providers:
  - anthropic
  - openai
  - gemini
commands:
  - name: init
    description: Scaffold a new project with program.md and eval harness
    example: ars init --template prompt-opt
  - name: run
    description: Run the autonomous experiment loop
    example: ars run --max-experiments 50
    flags:
      - "--max-experiments INT: Max experiments (default 100)"
      - "--provider TEXT: anthropic, openai, or gemini"
      - "--model TEXT: LLM model name"
      - "--dry-run: Validate setup only"
      - "--cloud: Run on AutoResearch Cloud"
      - "--lanes INT: Parallel lanes (cloud only)"
      - "--json: Output results as JSON"
  - name: results
    description: View experiment results table
    example: ars results --json
    flags:
      - "--json: JSON output"
      - "--csv: CSV output"
  - name: status
    description: Show run summary
    example: ars status --json
    flags:
      - "--json: JSON output"
      - "--cloud: Open cloud dashboard"
  - name: diff
    description: Show before/after comparison of optimized file
    example: ars diff --json
    flags:
      - "--json: JSON output"
      - "--raw: Raw git diff"
      - "--copy: Copy to clipboard"
  - name: apply
    description: Write best version to target file
    example: ars apply --yes
    flags:
      - "--yes: Skip confirmation"
      - "--target-file TEXT: Target file path"
  - name: config
    description: Manage CLI configuration
    subcommands:
      - "config show: Display all config + API key status"
      - "config set KEY VALUE: Set a default"
      - "config get KEY: Get a value"
  - name: login
    description: Authenticate with AutoResearch Cloud
    example: ars login
  - name: deploy
    description: Push local project to cloud
    example: ars deploy
  - name: upgrade
    description: View pricing plans
    example: ars upgrade
---

# AutoResearch CLI (ars)

Autonomous experiment loop runner. Define your optimization in a Markdown file, provide an eval harness, and let the AI agent run 100+ experiments overnight.

## Quick Start for AI Agents

```bash
# 1. Scaffold a project
ars init --template prompt-opt

# 2. Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Validate setup
ars run --dry-run

# 4. Run experiments (JSON output for parsing)
ars run --max-experiments 50

# 5. Get results as JSON
ars results --json
ars status --json
ars diff --json

# 6. Apply best version
ars apply --yes
```

## Agent Integration Notes

- All data commands support `--json` for machine-readable output
- `ars run --dry-run` validates setup without spending tokens
- `ars run` shows estimated API cost before starting
- Session state persists provider/model between runs (~/.autoresearch/session.json)
- Exit codes: 0 = success, 1 = error
- `results.tsv` in the working directory contains all experiment data (TSV format)
- The git branch `autoresearch/best` always contains the best version found

## Eval Harness Contract

Eval scripts must:
1. Print `metric_name:value` to stdout (e.g., `accuracy_pct:85.5`)
2. Exit 0 on success, non-zero on failure
3. Complete within 300 seconds

## Templates

| Template | Use Case | Metric |
|----------|----------|--------|
| prompt-opt | Optimize LLM prompts | accuracy_pct |
| config-tune | Tune config parameters | benchmark_score |
| copy-opt | Improve marketing copy | conversion_quality |
| test-pass | Fix code to pass tests | pass_pct |
| sop | Optimize SOPs | sop_quality |
