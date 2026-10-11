# Data dictionary

## Current: `data/raw/nyt_100_best_tv_shows_base.csv`

| Column | Description |
|---|---|
| `nyt_rank` | Rank on the NYT list (1-100) |
| `title` | Show title as printed by the NYT (season qualifier removed) |
| `nyt_years_raw` | Years as printed by the NYT (e.g., `2008-2013`, `2021-present`) |
| `start_year` | First year of the run |
| `end_year` | Last year of the run (blank if ongoing) |
| `status_per_nyt` | `ended` or `ongoing`, as labeled by the NYT list |
| `scope_note` | Notes on what is analyzed for a given entry |
| `analysis_scope` | `full_series` or `season_1_only` (applies to *True Detective* and *Beef*) |

## Planned fields (to be defined as collected)

`imdb_id`, `imdb_rating`, `imdb_votes`, `num_seasons`, `num_episodes`, `avg_episode_runtime_min`, `country`, `original_language`, `genres` (separate table), `original_network`, `network_type`, `production_companies` (separate table), `streaming_platform_us` (separate table), `streaming_checked_date`

## Rules (to confirm)

- **Runtime:** average episode length, documented per show.
- **Original network:** network of the first season; others kept separately.
- **Streaming availability:** one country (US), with the date checked.
- **Multi-genre shows:** each genre counted once per show in a separate table.
