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
| `authors` | string or list of strings | **yes** | Author name(s) of the underlying construction or paper |
| `developers` | string or list of strings | **yes** | Developer name(s) for the implementation |
| `url` | string (http/https URL) | no | Link to source code or paper |
| `commit` | string | no | Commit hash or version identifier |
| `date` | string (`YYYY-MM-DD`) | **yes** | Date the benchmark was measured; used as the x-axis on trend charts |
| `target` | string | no | Benchmark target id from `config/site.yaml` (e.g. `obfuscated-prf-110`, `witness-encryption-64`); defaults to the first configured target |
| `device` | string | no | Short GPU id the benchmark ran on (see `config/gpu_devices.yaml`, e.g. `H100`, `H200`, `A100`); used to derive cost. Cost is shown only when set |
| `obfuscation_latency_sec` | float >= 0 | **yes** | Obfuscation time in seconds |
| `obfuscation_total_time_hours` | float >= 0 | **yes** | Total obfuscation wall-clock time in hours |
| `obfuscation_peak_memory_gb` | float >= 0 | no | Obfuscation peak memory in GB; displayed as ND when omitted |
| `storage_gb` | float >= 0 | **yes** | Storage size (obfuscated circuit size) in GB |
| `evaluation_latency_sec` | float >= 0 | **yes** | Evaluation time in seconds |
| `evaluation_total_time_hours` | float >= 0 | **yes** | Total evaluation wall-clock time in hours |
| `evaluation_peak_memory_gb` | float >= 0 | no | Evaluation peak memory in GB; displayed as ND when omitted |

> **Cost is not a field.** Obfuscation/evaluation cost is derived automatically as
> the device's hourly price × total time. Hourly prices come from RunPod at build
> time (with an offline fallback in `config/gpu_devices.yaml`). To get cost shown
> for your entry, set `device` to a GPU id listed in `config/gpu_devices.yaml`;
> add a new id there if yours is missing.

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
| `unknown target` | Use one of the target ids defined in `config/site.yaml` |
| `url must be an http or https URL` | Use a full URL starting with `http://` or `https://` |

## PR process

1. Your PR triggers the `validate` workflow, which checks your YAML and runs the test suite.
2. A maintainer reviews and merges.
3. On merge to `main`, the site rebuilds and deploys automatically.
