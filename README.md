# ObfusBench

Public benchmark leaderboard for iO (indistinguishability obfuscation) implementations.

## Overview

ObfusBench is a static website that collects and displays benchmark results for iO implementations on a standard benchmark circuit. New entries are submitted via GitHub pull requests containing YAML files.

**Stack:** Python 3.12, Jinja2, PyYAML, Pydantic v2, vanilla CSS/JS, GitHub Actions, GitHub Pages.

## Local setup

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package and test dependencies
pip install -e ".[test]"
```

## Usage

### Validate benchmarks

```bash
python -m sitegen validate
```

This reads all YAML files under `benchmarks/`, validates them, and regenerates `schema/benchmark.schema.json`.

### Build the site

```bash
python -m sitegen build --output site
```

Generates the full static site into `site/`. During the build, current GPU
hourly prices are fetched from the RunPod API to derive benchmark cost (see
[Cost & GPU pricing](#cost--gpu-pricing)). Set `OBFUSBENCH_NO_FETCH=1` to skip the
network call (cost then renders as ND).

### Preview locally

```bash
python -m http.server 8000 --directory site
```

Then open http://localhost:8000.

### Run tests

```bash
pytest -v
```

## Cost & GPU pricing

Obfuscation and evaluation **cost is derived, never stored** in benchmark YAML:

```
cost = device hourly price (USD) × total time (hours)
```

- Each benchmark's `device` field is a short GPU id (e.g. `H200`).
- `config/gpu_devices.yaml` maps each id to a specific RunPod GPU type.
- At build time, `sitegen/pricing.py` queries the public RunPod GraphQL API and
  uses the **community-cloud** hourly price for each device.
- If the fetch fails, or a device is unset/unknown, cost renders as **ND** — there
  is no committed fallback price.

Cost is shown in the leaderboard table (under the total-time columns) and in the
tooltips of the total-time trend charts. The benchmark YAML schema does not
include cost fields.

## Deployment

The site deploys automatically to GitHub Pages via `.github/workflows/deploy.yml`:

- on every push to `main`, and
- **hourly on a schedule** (`cron: "17 * * * *"`), so the published site refreshes
  RunPod prices roughly once an hour. (GitHub schedules are best-effort and may be
  delayed; scheduled runs also pause after ~60 days of repository inactivity.)

The RunPod pricing query is public, so no credentials are required. A
`RUNPOD_API_KEY` secret is referenced by the build as an optional safety net in
case RunPod ever requires auth.

### Manual GitHub settings required

1. **GitHub Pages:** Go to Settings > Pages and set the source to **GitHub Actions**.
2. **CODEOWNERS:** Replace `@REPLACE_WITH_GITHUB_USERNAME_OR_TEAM` in `.github/CODEOWNERS` with a real GitHub username or team.
3. **Branch protection (recommended):** Enable branch protection on `main` and require the `validate` status check to pass before merging.

## Adding a benchmark

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. In short:

1. Copy `examples/benchmark.example.yaml` to `benchmarks/<your-slug>.yaml`
2. Fill in your data
3. Run `python -m sitegen validate`
4. Open a pull request

## License

See [LICENSE](LICENSE).
