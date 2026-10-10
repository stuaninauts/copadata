# CopaData

Data-analysis engine for the FIFA Men's World Cup, **1986-2026**, built on public datasets
with **no API key** (see [Data sources](#data-sources)).

Downloads the matches, computes time and decision metrics (winning goal, late goal, extra-time
goal, comeback, survival goal) and each team's situation within its group, and materializes
every edition to Parquet ready for analysis and comparison across World Cups.

## Run

```bash
pip install -r requirements.txt
python -m copadata.pipeline            # download both sources and reprocess every edition
python -m copadata.pipeline --offline  # reprocess the raw files already downloaded
```

Tests (metric definitions, historical adapter and git hooks):

```bash
python -m pytest
```

Contributing: branches `<type>/<description>` off `main`, PRs merged by rebase, and
[Conventional Commits](https://www.conventionalcommits.org/) enforced by a git hook. Enable it once per clone:

```bash
git config core.hooksPath .githooks
```

The pipeline is **idempotent and cumulative**: re-running picks up new matches as the
tournament progresses.

## Outputs (`data/processed/`)

Every file carries a `year` column (one World Cup per value); `match_id` is unique across editions.

| File | Grain | Contents |
|---|---|---|
| `matches.parquet` | 1 row/match | score, stage, margin, extra time / penalties, time & decision metrics |
| `team_matches.parquet` | 2 rows/match | each team's perspective + group situation (matchday, points/position before the match) |
| `goals.parquet` | 1 row/goal | minute, extra time, late goal, own goal, penalty |

## Structure

```
copadata/   ingest · fjelstul (historical adapter) · transform · derive · metrics · pipeline · config
tests/      metric definitions, historical adapter and git hooks
docs/adr/   architecture decision records (PT)
data/       raw/ (raw snapshot)   ·   processed/ (parquets)
```

Metric definitions are concentrated in `copadata/metrics.py`.

## Data sources

| Editions | Source | License |
|---|---|---|
| 2026 | [OpenFootball `worldcup.json`](https://github.com/openfootball/worldcup.json) | Public domain (CC0) |
| 1986-2022 | [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup), pinned commit in `copadata/config.py` | [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode) |

Both are downloaded at run time into `data/raw/` and are not redistributed by this repository.
Why two sources: [ADR 0005](docs/adr/0005-fonte-historica-fjelstul.md).

**Attribution (Fjelstul World Cup Database):** The Fjelstul World Cup Database © 2023 Joshua C. Fjelstul, Ph.D.,
licensed under [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode),
available at https://www.github.com/jfjelstul/worldcup. **Modifications:** only men's World Cups from 1986
are used; matches and goals are reshaped into the OpenFootball format (`copadata/fjelstul.py`) to compute
the metrics in this repository. Data derived from it is shared under the same license.

## Next

A public, bilingual (EN/PT) web version is planned at `copa.stuaninauts.com`: one page per question
(answer, `k/n`, caveat, chart, table, method, download) plus an explorer, built with Astro from data
exported by the pipeline. Decisions in [ADR 0006](docs/adr/0006-camada-de-publicacao.md) and
[ADR 0007](docs/adr/0007-site-web.md).

Idea for later: natural-language Q&A with an LLM, limited to searching the curated questions and always
citing their `n`. Out of the first version.

---

> 🚧 Work in progress.
