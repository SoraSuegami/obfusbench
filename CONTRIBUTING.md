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
| `paper_url` | string (http/https URL) | no | Link to the paper / writeup of the construction |
| `implementation_url` | string (http/https URL) | no | Link to the implementation source code |
| `commit` | string | no | Commit hash or version identifier (links the commit when `implementation_url` is a GitHub repo) |
| `date` | string (`YYYY-MM-DD`) | **yes** | Date the benchmark was measured; used as the x-axis on trend charts |
| `target` | string | no | Benchmark target id from `config/site.yaml` (e.g. `obfuscated-prf-110`, `witness-encryption-64`); defaults to the first configured target |
| `device` | string | no | Short GPU id the benchmark ran on (see `config/gpu_devices.yaml`, e.g. `H100`, `H200`, `A100`); used to derive cost. Cost is shown only when set |
| `<phase1>_latency_min` | float >= 0 | **yes** | Phase-1 single-run latency in **minutes** (preferred). Alternatively give `<phase1>_latency_sec` in seconds; it is converted to minutes (÷60). Provide only one of the two |
| `<phase1>_total_time_hours` | float >= 0 | **yes** | Total phase-1 wall-clock time in hours |
| `<phase1>_peak_memory_gb` | float >= 0 | no | Phase-1 peak memory in GB; displayed as ND when omitted |
| `<size>` | float >= 0 | **yes** | Output size in GB |
| `<phase2>_latency_min` | float >= 0 | **yes** | Phase-2 single-run latency in **minutes** (preferred). Alternatively give `<phase2>_latency_sec` in seconds; it is converted to minutes (÷60). Provide only one of the two |
| `<phase2>_total_time_hours` | float >= 0 | **yes** | Total phase-2 wall-clock time in hours |
| `<phase2>_peak_memory_gb` | float >= 0 | no | Phase-2 peak memory in GB; displayed as ND when omitted |

Latency is displayed in minutes throughout the site. Supply `<phase1>_latency_min`
(preferred); the seconds form `<phase1>_latency_sec` is still accepted and
converted to minutes at load time. Giving both units for the same phase is an
error.

#### Metric field names depend on the target

The seven metric fields above use **target-specific key names** (defined by each
target's `labels` in `config/site.yaml`). Use the names matching your `target`;
using another target's names is rejected with a hint.

| Generic | `obfuscated-prf-110` (default) | `witness-encryption-64` |
|---|---|---|
| `<phase1>_latency_min` | `obfuscation_latency_min` | `encryption_latency_min` |
| `<phase1>_total_time_hours` | `obfuscation_total_time_hours` | `encryption_total_time_hours` |
| `<phase1>_peak_memory_gb` | `obfuscation_peak_memory_gb` | `encryption_peak_memory_gb` |
| `<size>` | `storage_gb` | `ciphertext_size_gb` |
| `<phase2>_latency_min` | `evaluation_latency_min` | `decryption_latency_min` |
| `<phase2>_total_time_hours` | `evaluation_total_time_hours` | `decryption_total_time_hours` |
| `<phase2>_peak_memory_gb` | `evaluation_peak_memory_gb` | `decryption_peak_memory_gb` |

The seconds alias for latency follows the same renaming: e.g.
`obfuscation_latency_sec` / `encryption_latency_sec`.

`examples/benchmark.example.yaml` uses the default-target names. For another
target, rename these keys per the table above.

#### Optional: per-step breakdowns

You may also add ordered (pipeline-order) breakdowns showing where each phase
spends its total time and what makes up the output size. These render on your
detail page as a 100% stacked bar plus a share table.

| Generic | `obfuscated-prf-110` (default) | `witness-encryption-64` | Item fields |
|---|---|---|---|
| `<phase1>_time_breakdown` | `obfuscation_time_breakdown` | `encryption_time_breakdown` | `step`, `time_hours` |
| `<phase2>_time_breakdown` | `evaluation_time_breakdown` | `decryption_time_breakdown` | `step`, `time_hours` |
| `<phase1>_size_breakdown` | `obfuscation_size_breakdown` | `encryption_size_breakdown` | `component`, `size_gb` |

Each is a list of items, e.g.:

```yaml
obfuscation_time_breakdown:
  - step: "Trapdoor sampling"
    time_hours: 5.17e45
  - step: "Matrix encoding"
    time_hours: 3.81e45
```

Sub-steps need not sum to the phase total — the site fills any remainder into an
"Other" slice. A breakdown whose sub-steps sum to **more** than the phase total
is rejected. Omit any breakdown you don't have.

### Cost is derived, not submitted

Obfuscation and evaluation cost are **not** YAML fields. Each is computed as:

```
cost = device hourly price (USD) × total time (hours)
```

The hourly price comes from the **RunPod community-cloud price**, fetched live at
build time. The `device` field is a short GPU id (e.g. `H200`) that
`config/gpu_devices.yaml` maps to a specific RunPod GPU type.

- To get cost displayed for your entry, set `device` to an id listed in
  `config/gpu_devices.yaml`. If your GPU is missing, add a new id there (map it to
  the matching RunPod GPU type name).
- Bare model names like `H100` are ambiguous on RunPod (SXM / NVL / PCIe); the
  registry pins one variant per id — add a more specific id if you need another.
- If the live price can't be fetched, or `device` is unset/unknown, cost shows as
  **ND**. There is no committed fallback price.

Cost appears in the leaderboard table (under the total-time columns) and in the
tooltips of the total-time trend charts.

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
| `provide latency in one unit only` | Give either `<phase>_latency_min` or `<phase>_latency_sec`, not both |

## PR process

1. Your PR triggers the `validate` workflow, which checks your YAML and runs the test suite.
2. A maintainer reviews and merges.
3. On merge to `main`, the site rebuilds and deploys automatically.
