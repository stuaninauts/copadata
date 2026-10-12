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

The pipeline is **idempotent**: every source is pinned to a commit, so every run gives the same tables.

## Outputs (`data/processed/`)

Every file carries a `year` column (one World Cup per value); `match_id` is unique across editions.

| File | Grain | Contents |
|---|---|---|
| `matches.parquet` | 1 row/match | score, stage, margin, extra time / penalties, time & decision metrics, pre-match Elo |
| `team_matches.parquet` | 2 rows/match | each team's perspective + group situation (matchday, points/position/zone before the match) + Elo |
| `goals.parquet` | 1 row/goal | minute, extra time, late goal, stoppage-time goal, final-quarter goal, own goal, penalty |
| `penalty_kicks.parquet` | 1 row/kick | shootout kicks of 1986-2022, in order, and whether a miss eliminates (none for 2026) |
| `international.parquet` | 1 row/match | every international match since 1872 with pre-match Elo, weight and shootout |
| `international_goals.parquet` | 1 row/goal | goals of those matches with minute |

## Public data export (`web/public/data/`)

```bash
python -m copadata.export          # write the aggregates (JSON + CSV) and full tables (CSV + Parquet)
python -m copadata.export --check  # fail if the committed export is out of date
```

The export is versioned and is what the web site reads: aggregate tables by edition, era and the pooled
1986-2022 history, every rate with `k` and `n`; tables, columns and source commits in `manifest.json`.
It also carries the **myths** (`myths.json` and one `myth_*` table each): a closed list of popular claims
tested against the data, each with one effect, one interval and a verdict from a rule fixed before running
([ADR 0008](docs/adr/0008-mitos-lista-fechada.md)).
It is derived from the Fjelstul data, so it is licensed **CC-BY-SA 4.0** (attribution in its `README.md`).

## Structure

```
copadata/   ingest · fjelstul (historical adapter) · transform · derive · metrics · aggregate · export · pipeline · config
tests/      metric definitions, aggregates (incl. golden findings), historical adapter and git hooks
docs/adr/   architecture decision records (PT)
data/       raw/ (raw snapshot)   ·   processed/ (parquets)
web/        Astro site (ADR 0007, 0010) · public/data/ (versioned export, CC-BY-SA 4.0)
```

Metric definitions are concentrated in `copadata/metrics.py`; the aggregates behind the findings
(rates and means by edition, era, stage, with `k` and `n`) in `copadata/aggregate.py`.

## Web site (`web/`)

Static Astro site for `copa.stuaninauts.com`. It reads the export at build time: page texts live in
`web/src/content/` and cite numbers by reference to the export, so a number that does not exist breaks the build.
Charts are SVG drawn by Observable Plot during the build; no script runs in the browser.

```bash
cd web
npm install
npm run check && npm run build   # type check, then build (the CSP only exists in the build)
npm run preview                  # serve dist/ locally
```

Deploy: Cloudflare Workers Builds builds `web/` and publishes it on every merge to `main` (`web/wrangler.jsonc`:
static assets only, custom domain, no `*.workers.dev`); pull requests get a preview URL. CI (`.github/workflows/ci.yml`)
runs the pipeline, the tests, `export --check`, the site build and `reuse lint` on every pull request. Python versions
in CI are pinned in `constraints.txt`, because the export is checked byte for byte.

## Data sources

| Editions | Source | License |
|---|---|---|
| 2026 | [OpenFootball `worldcup.json`](https://github.com/openfootball/worldcup.json), pinned commit in `copadata/config.py` | Public domain (CC0) |
| 1986-2022 | [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup), pinned commit in `copadata/config.py` | [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode) |
| Elo (1872-2026) | [International football results](https://github.com/martj42/international_results), pinned commit in `copadata/config.py`; ratings computed in `copadata/elo.py` ([ADR 0009](docs/adr/0009-forca-das-selecoes-elo.md)) | Public domain (CC0) |

Both are downloaded at run time into `data/raw/`; the raw files are not redistributed by this repository.
Why two sources: [ADR 0005](docs/adr/0005-fonte-historica-fjelstul.md).

**Attribution (Fjelstul World Cup Database):** The Fjelstul World Cup Database © 2023 Joshua C. Fjelstul, Ph.D.,
licensed under [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode),
available at https://www.github.com/jfjelstul/worldcup. **Modifications:** only men's World Cups from 1986
are used; matches and goals are reshaped into the OpenFootball format (`copadata/fjelstul.py`) to compute
the metrics in this repository. Data derived from it is shared under the same license.

**License:** code and docs are MIT; the data export in `web/public/data/` is CC-BY-SA 4.0
(per-path licensing in `REUSE.toml`, texts in `LICENSES/`).

## Next

A public, bilingual (EN/PT) web version is planned at `copa.stuaninauts.com`: one page per question
(answer, `k/n`, caveat, chart, table, method, download) plus an explorer, built with Astro from data
exported by the pipeline. Decisions in [ADR 0006](docs/adr/0006-camada-de-publicacao.md) and
[ADR 0007](docs/adr/0007-site-web.md).

Idea for later: natural-language Q&A with an LLM, limited to searching the curated questions and always
citing their `n`. Out of the first version.

---

> 🚧 Work in progress.
