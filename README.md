# The NYT 100, By the Numbers

A data analytics project on *The New York Times'* list **"The 100 Best TV Shows of the 21st Century"** (published September 20, 2026).

> **Status: in progress.** The base dataset is built; data collection, analysis, and dashboard are next.

## Main question (working title)

**What does a great show look like?**
What do the NYT's 100 best shows have in common, and how do they differ (era, length, format, genre, network/platform, country)? The final question may be refined as the project develops.

## Scope

- Dataset of the 100 shows on the list (no critic-vs-audience focus; the goal is to profile and compare the shows on the list itself).
- Shows listed for a single season (*True Detective*, *Beef*) are analyzed on that season only.
- Findings describe **this list only**. It is an editorial selection of 100 shows, so results are not generalizable to TV as a whole.

## Planned pipeline

1. **Collect** - Python: metadata from TMDB (genres, seasons, episodes, networks, production companies, country, runtime) and IMDb non-commercial datasets (IMDb ID, rating, votes)
2. **Clean** - pandas, with a changelog of every cleaning decision
3. **Store** - SQLite database (shows, genres, companies, platforms tables) and analysis queries
4. **Analyze** - exploratory notebook (distributions, time trends, show groupings)
5. **Visualize** - interactive dashboard in Tableau Public

## Tools 
Python (pandas, requests, matplotlib), SQLite, Tableau Public, Git/GitHub

## Progress

- [x] Base dataset from the NYT list (rank, title, years, status)
- [ ] TMDB / IMDb data collection
- [ ] Data cleaning and data dictionary
- [ ] SQL database and queries
- [ ] Analysis notebook
- [ ] Dashboard
- [ ] Final write-up and key findings

## Repository structure

```
data/raw/         original data (NYT base list)
data/processed/   cleaned datasets
scripts/          data collection and cleaning scripts
notebooks/        exploratory analysis
sql/              schema and queries
dashboard/        dashboard files and screenshots
docs/             data dictionary and notes
```

## Data sources and attribution

- Show list and ranking: *The New York Times*, "The 100 Best TV Shows of the 21st Century" (nytimes.com/bestTV). Used for non-commercial, educational analysis.
- This product uses the TMDB API but is not endorsed or certified by TMDB.
- Streaming availability data (when added) is provided by JustWatch via TMDB.
- Ratings and votes (when added): IMDb non-commercial datasets (imdb.com/interfaces). Raw IMDb files are not redistributed in this repository.

## Disclaimer

This is a non-commercial project created for educational and personal portfolio purposes. It is not affiliated with or endorsed by The New York Times, TMDB, IMDb, or JustWatch. All show titles, rankings, and third-party data belong to their respective owners.

## Author

Maria Leal
