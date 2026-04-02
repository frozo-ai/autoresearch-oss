#!/usr/bin/env bash
# Eval harness for config-tune template.
# Reads config.yaml and computes a benchmark_score based on parameter tuning.
# The scoring function simulates a realistic system where parameters interact.
#
# Requirements: python3, pyyaml (pip install pyyaml)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 - "$SCRIPT_DIR/config.yaml" << 'PYEOF'
import sys
import math
import yaml

config_path = sys.argv[1]
with open(config_path, "r") as f:
    cfg = yaml.safe_load(f)

# Extract values
workers = cfg.get("workers", 4)
queue_size = cfg.get("queue_size", 128)
timeout_ms = cfg.get("timeout_ms", 5000)
cache_size_mb = cfg.get("cache_size_mb", 256)
cache_ttl_seconds = cfg.get("cache_ttl_seconds", 300)
cache_compression = cfg.get("cache_compression", False)
batch_size = cfg.get("batch_size", 32)
max_retries = cfg.get("max_retries", 3)
retry_backoff = cfg.get("retry_backoff", 2.0)
max_memory_mb = cfg.get("max_memory_mb", 2048)
gc_interval_seconds = cfg.get("gc_interval_seconds", 60)

# Validate ranges
errors = []
if not (1 <= workers <= 64): errors.append(f"workers={workers} out of range [1,64]")
if not (16 <= queue_size <= 4096): errors.append(f"queue_size={queue_size} out of range [16,4096]")
if not (100 <= timeout_ms <= 30000): errors.append(f"timeout_ms={timeout_ms} out of range [100,30000]")
if not (64 <= cache_size_mb <= 8192): errors.append(f"cache_size_mb={cache_size_mb} out of range [64,8192]")
if not (10 <= cache_ttl_seconds <= 3600): errors.append(f"cache_ttl_seconds={cache_ttl_seconds} out of range [10,3600]")
if not isinstance(cache_compression, bool): errors.append(f"cache_compression must be true/false")
if not (1 <= batch_size <= 512): errors.append(f"batch_size={batch_size} out of range [1,512]")
if not (0 <= max_retries <= 10): errors.append(f"max_retries={max_retries} out of range [0,10]")
if not (1.0 <= retry_backoff <= 5.0): errors.append(f"retry_backoff={retry_backoff} out of range [1.0,5.0]")
if not (512 <= max_memory_mb <= 32768): errors.append(f"max_memory_mb={max_memory_mb} out of range [512,32768]")
if not (5 <= gc_interval_seconds <= 300): errors.append(f"gc_interval_seconds={gc_interval_seconds} out of range [5,300]")

if errors:
    for e in errors:
        print(f"VALIDATION ERROR: {e}", file=sys.stderr)
    print("benchmark_score:0.0")
    sys.exit(0)

# ---- Scoring Function ----
# Simulates a system where throughput, latency, and resource efficiency interact.
# The optimal configuration requires balancing multiple trade-offs.

# Throughput component (0-30 pts): workers * batch_size sweet spot around 16*64
throughput_raw = workers * batch_size
throughput_score = 30.0 * math.exp(-((math.log(throughput_raw) - math.log(1024)) ** 2) / 2.0)

# Latency component (0-25 pts): lower timeout + right queue/worker ratio
queue_ratio = queue_size / max(workers, 1)
latency_score = 25.0 * math.exp(-((queue_ratio - 32) ** 2) / 800.0)
timeout_factor = 1.0 - (timeout_ms - 100) / 29900  # prefer lower timeout
latency_score *= (0.5 + 0.5 * timeout_factor)

# Cache component (0-25 pts): bigger cache + moderate TTL + compression bonus
cache_score = 25.0 * (1.0 - math.exp(-cache_size_mb / 2048.0))
ttl_factor = math.exp(-((cache_ttl_seconds - 120) ** 2) / 50000.0)
cache_score *= ttl_factor
if cache_compression:
    cache_score *= 1.3  # 30% bonus for compression
cache_score = min(cache_score, 25.0)

# Resilience component (0-10 pts): moderate retries + low backoff
resilience_score = 10.0 * math.exp(-((max_retries - 2) ** 2) / 4.0)
backoff_factor = math.exp(-((retry_backoff - 1.5) ** 2) / 2.0)
resilience_score *= backoff_factor

# Efficiency component (0-10 pts): memory/cache ratio + GC interval
mem_ratio = max_memory_mb / max(cache_size_mb, 1)
efficiency_score = 10.0 * math.exp(-((mem_ratio - 4.0) ** 2) / 8.0)
gc_factor = math.exp(-((gc_interval_seconds - 30) ** 2) / 2000.0)
efficiency_score *= gc_factor

total = throughput_score + latency_score + cache_score + resilience_score + efficiency_score
total = max(0.0, min(100.0, total))

print(f"Throughput component:  {throughput_score:.1f}/30")
print(f"Latency component:    {latency_score:.1f}/25")
print(f"Cache component:      {cache_score:.1f}/25")
print(f"Resilience component: {resilience_score:.1f}/10")
print(f"Efficiency component: {efficiency_score:.1f}/10")
print(f"")
print(f"benchmark_score:{total:.1f}")
PYEOF
