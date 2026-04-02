# Config Tuning

## Goal
Maximize the benchmark_score of a simulated system by tuning parameters in config.yaml, measured as benchmark_score (0-100 scale).

## Setup
1. Read `config.yaml` to understand the tunable parameters and their current values.
2. Read `eval.sh` to understand how the benchmark score is computed.
3. Run the eval once to get the baseline score.

## Constraints
- DO NOT MODIFY: `eval.sh`
- Only modify `config.yaml`
- All parameter values must remain within the valid ranges documented in config.yaml comments
- The config must remain valid YAML

## Experiment Loop
1. Analyze the scoring function in eval.sh, then adjust one or more parameters in `config.yaml`
2. Run: `bash eval.sh`
3. Read metric: parse `benchmark_score:<value>` from stdout
4. If improved: keep the change to `config.yaml`
5. If not improved: revert `config.yaml` to the previous version
6. LOOP FOREVER

## Metric
metric_name: benchmark_score
higher_is_better: true
