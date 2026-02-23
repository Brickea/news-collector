# news-collector

A configurable daily news-digest tool that fetches articles from RSS/Atom
feeds, generates a dated **Markdown** file with every item linked back to its
original URL, and automatically archives older digests.  The entire pipeline
runs as a **GitHub Actions** workflow on a daily schedule.

---

## Features

| Feature | Description |
|---------|-------------|
| **Configurable categories** | Choose which news topics to collect (technology, world, business, health, science, …). |
| **Configurable sources** | Enable/disable individual RSS/Atom feeds per run; add new sources in seconds. |
| **X / Twitter support** | Follow X accounts via a Nitter RSS proxy (see [Adding X/Twitter sources](#adding-xtwitter-sources)). |
| **Markdown output** | Each digest is a readable `YYYY-MM-DD.md` file; every headline links to its original article. |
| **Archiving** | Older digests are automatically moved into `docs/archive/YYYY/MM/` (format configurable). |
| **GitHub Actions automation** | Daily schedule + manual trigger; results committed back to the repository. |

---

## Quick start

### 1 · Install dependencies

```bash
pip install -r requirements.txt
```

### 2 · Edit the configuration

Open `config/config.yaml` and adjust:

* **`categories`** – the list of topic categories you want to collect.
* **`sources`** – enable/disable feeds and add your own.
* **`output`** – where files are written.
* **`archive`** – whether and how to archive old digests.

### 3 · Run locally

```bash
python src/collector.py
# or specify a custom config path:
python src/collector.py path/to/my-config.yaml
```

The digest is written to `docs/YYYY-MM-DD.md`.

---

## Configuration reference

```yaml
# Categories you want to collect.
# Only sources whose 'categories' list overlaps with this list will be fetched.
categories:
  - technology
  - business
  - world
  - health
  - science

sources:
  - name: TechCrunch          # Display name (used as a section heading)
    type: rss                 # "rss" (Atom feeds also work)
    url: https://techcrunch.com/feed/
    categories: [technology]  # Which categories this source covers
    enabled: true             # Set false to temporarily skip
    max_items: 10             # (optional) override global max_items_per_source

output:
  dir: docs                   # Where to write today's digest
  archive_dir: docs/archive   # Root of the archive tree
  max_items_per_source: 10    # Global default for maximum articles per source

archive:
  enabled: true               # Move old digests to the archive directory
  format: "%Y/%m"             # strftime format for archive sub-directory
                              # e.g. "%Y/%m" → docs/archive/2024/03/
                              #      "%Y"    → docs/archive/2024/
```

---

## Adding X/Twitter sources

X (formerly Twitter) does not offer a public RSS feed, but you can follow
accounts through a [Nitter](https://nitter.net) instance that exposes one.

```yaml
sources:
  - name: "X: @NASA"
    type: rss
    url: https://<your-nitter-instance>/NASA/rss
    categories: [science]
    enabled: true
```

> **Note:** Nitter instances come and go.  Find an active one at
> <https://github.com/zedeus/nitter/wiki/Instances>.

---

## GitHub Actions automation

The workflow file `.github/workflows/collect-news.yml` runs the collector
automatically:

* **Scheduled** – every day at **08:00 UTC**.
* **Manual** – trigger *workflow_dispatch* from the GitHub Actions UI at any
  time with optional overrides (see below).

After a successful run the generated/archived files are committed back to the
repository with the message `📰 Daily news digest YYYY-MM-DD`.

### Manually triggering a collection run

1. Open the repository on GitHub.
2. Click **Actions** → **Collect News** → **Run workflow**.
3. Fill in the optional inputs:

| Input | Description | Example |
|-------|-------------|---------|
| `config_path` | Path to the config YAML (relative to the repo root). | `config/config.yaml` |
| `categories` | Comma-separated list of categories to collect. Leave empty to use the categories defined in the config file. | `technology,world` |

4. Click **Run workflow**.

You can also use the [GitHub CLI](https://cli.github.com/):

```bash
# Run with default config
gh workflow run collect-news.yml

# Override categories for a one-off run
gh workflow run collect-news.yml \
  --field categories="technology,health"

# Use a different config file
gh workflow run collect-news.yml \
  --field config_path="config/my-config.yaml"
```

### Running locally with the same overrides

```bash
# Collect only technology and world news
python src/collector.py --categories technology,world

# Use a custom config and override categories
python src/collector.py path/to/config.yaml --categories science
```

### Required permissions

The workflow needs `contents: write` permission to commit files.  This is set
in the workflow file; no extra setup is required for public repositories.

For **private repositories** make sure *Settings → Actions → General →
Workflow permissions* is set to **"Read and write permissions"**.

---

## Running tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/
```

---

## Project structure

```
news-collector/
├── .github/
│   └── workflows/
│       └── collect-news.yml   # Daily automation
├── config/
│   └── config.yaml            # Edit this to customise behaviour
├── docs/
│   ├── README.md
│   ├── YYYY-MM-DD.md          # Today's digest (auto-generated)
│   └── archive/
│       └── YYYY/MM/           # Archived digests
├── src/
│   └── collector.py           # Main script
├── tests/
│   └── test_collector.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```