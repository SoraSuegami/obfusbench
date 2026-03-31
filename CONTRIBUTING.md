# Contributing to ObfusBench

Thank you for contributing a benchmark entry! This guide explains how to submit your iO implementation results.

## How to add a benchmark

1. **Fork this repository** and clone your fork.

2. **Copy the example file:**
   ```bash
   cp examples/benchmark.example.yaml benchmarks/<your-implementation-slug>.yaml
   ```
   Use a short, descriptive filename in kebab-case (e.g., `my-io-impl.yaml`).

3. **Fill in your data** — see the schema reference below.

4. **Validate locally:**
   ```bash
   pip install -e .
   python -m sitegen validate
   ```

5. **Open a pull request** against `main`. The CI will validate your file automatically.

## Schema reference

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | **yes** | Display name for your implementation (must be unique) |
| `authors` | string or list of strings | **yes** | Author name(s) |
| `url` | string (http/https URL) | no | Link to source code or paper |
| `commit` | string | no | Commit hash or version identifier |
| `obfuscation_latency_sec` | float >= 0 | **yes** | Obfuscation time in seconds |
| `obfuscation_cost_usd` | float >= 0 | **yes** | Obfuscation cost in USD |
| `obfuscation_peak_memory_gb` | float >= 0 | **yes** | Obfuscation peak memory in GB |
| `obfuscated_circuit_size_gb` | float >= 0 | **yes** | Obfuscated circuit size in GB |
| `evaluation_latency_sec` | float >= 0 | **yes** | Evaluation time in seconds |
| `evaluation_cost_usd` | float >= 0 | **yes** | Evaluation cost in USD |
| `evaluation_peak_memory_gb` | float >= 0 | **yes** | Evaluation peak memory in GB |

## File naming conventions

- Place your file in `benchmarks/`
- Use `.yaml` extension
- Use lowercase kebab-case for the filename (e.g., `my-implementation.yaml`)
- One implementation per file

## Common validation errors

| Error | Fix |
|---|---|
| `id: non-empty string` | Make sure `id` is not blank |
| `must be non-negative` | All numeric metrics must be >= 0 |
| `must be finite` | No `inf` or `NaN` values |
| `extra fields not permitted` | Remove unknown keys — check for typos |
| `Duplicate id` | Choose a unique `id` |
| `url must be an http or https URL` | Use a full URL starting with `http://` or `https://` |

## PR process

1. Your PR triggers the `validate` workflow, which checks your YAML and runs the test suite.
2. A maintainer reviews and merges.
3. On merge to `main`, the site rebuilds and deploys automatically.
