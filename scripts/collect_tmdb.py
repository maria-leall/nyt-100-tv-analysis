"""
Collect TMDB data for the NYT 100 Best TV Shows list.

Reads:   data/raw/nyt_100_best_tv_shows_base.csv
         data/raw/tmdb_overrides.csv   (optional: columns nyt_rank,tmdb_id)
Writes:  data/processed/shows_tmdb.csv          one row per show
         data/processed/show_genres.csv         linking tables (one row per show per item)
         data/processed/show_networks.csv
         data/processed/show_companies.csv
         data/processed/show_streaming_us.csv
         data/processed/review_needed.csv       shows to check by hand

Usage:
    python scripts/collect_tmdb.py --limit 3      # quick test on 3 shows
    python scripts/collect_tmdb.py                # full run
    python scripts/collect_tmdb.py --skip-runtime # faster, no per-episode runtime

The API key is read from the TMDB_API_KEY environment variable
(a GitHub Codespaces secret). It is never stored in the code.
"""
import argparse
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.themoviedb.org/3"
ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "nyt_100_best_tv_shows_base.csv"
OVERRIDES_FILE = ROOT / "data" / "raw" / "tmdb_overrides.csv"
OUT_DIR = ROOT / "data" / "processed"

session = requests.Session()


def get_key():
    key = os.environ.get("TMDB_API_KEY")
    if not key:
        try:  # optional local fallback: a .env file (never commit it)
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            key = os.environ.get("TMDB_API_KEY")
        except ImportError:
            pass
    if not key:
        sys.exit("No API key found. Set the TMDB_API_KEY environment variable "
                 "(Codespaces secret) and try again.")
    return key.strip()

def api_get(path, key, **params):
    """Send one request to TMDB. Returns parsed JSON, or None if not found/failed."""
    params["api_key"] = key
    for attempt in range(4):
        try:
            r = session.get(f"{BASE_URL}{path}", params=params, timeout=20)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200:
            time.sleep(0.05)  # be polite to the API
            return r.json()
        if r.status_code == 401:
            sys.exit("TMDB rejected the API key (401). Check your TMDB_API_KEY secret.")
        if r.status_code == 404:
            return None
        if r.status_code == 429:  # too many requests: wait and retry
            time.sleep(int(r.headers.get("Retry-After", 2)) + 1)
            continue
        time.sleep(2)
    return None


def norm(text):
    text = re.sub(r"\(.*?\)", "", str(text).lower())
    text = text.replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", text)


def search_show(title, year, key):
    """Find the TMDB id for a show. Returns (tmdb_id, match_quality)."""
    query = re.sub(r"\s*\(.*?\)", "", title).strip()
    results = []
    for yr in (year, None):  # try with the start year, then without
        params = {"query": query}
        if yr:
            params["first_air_date_year"] = int(yr)
        data = api_get("/search/tv", key, **params)
        results = (data or {}).get("results", [])
        if results:
            break
    if not results:
        return None, "not_found"
    for cand in results:
        same_name = norm(cand.get("name", "")) == norm(query) or \
            norm(cand.get("original_name", "")) == norm(query)
        same_year = str(cand.get("first_air_date", ""))[:4] == str(int(year))
        if same_name and same_year:
            return cand["id"], "exact"
    for cand in results:
        if norm(cand.get("name", "")) == norm(query):
            return cand["id"], "check_year"
    return results[0]["id"], "check_name"

def season_stats(tid, season_numbers, key, today):
    """Count aired episodes and average runtime across the given seasons."""
    n_eps, mins = 0, []
    for sn in season_numbers:
        sd = api_get(f"/tv/{tid}/season/{sn}", key)
        if not sd:
            continue
        for ep in sd.get("episodes", []):
            air = ep.get("air_date")
            if air and air > today:  # not aired yet
                continue
            n_eps += 1
            if ep.get("runtime"):
                mins.append(ep["runtime"])
    avg = round(sum(mins) / len(mins), 1) if mins else None
    return n_eps, avg


def names(items):
    return [i["name"] for i in (items or []) if i.get("name")]

def collect_one(row, key, overrides, skip_runtime, today):
    """Return (show_dict, genres, networks, companies, streaming, review_reasons)."""
    rank, title = int(row["nyt_rank"]), row["title"]
    reasons = []

    if rank in overrides:
        tid, quality = int(overrides[rank]), "manual_override"
    else:
        tid, quality = search_show(title, row["start_year"], key)
    if tid is None:
        return {"tmdb_match": "not_found"}, [], [], [], [], ["no TMDB match"]
    if quality in ("check_year", "check_name"):
        reasons.append(f"match uncertain ({quality})")

    d = api_get(f"/tv/{tid}", key, append_to_response="external_ids,watch/providers")
    if not d:
        return {"tmdb_id": tid, "tmdb_match": quality}, [], [], [], [], ["details request failed"]

    seasons = [s for s in d.get("seasons", []) if s.get("season_number", 0) >= 1]
    scope = str(row.get("analysis_scope", ""))
    m = re.match(r"season_(\d+)_only", scope)
    if m:
        seasons = [s for s in seasons if s["season_number"] == int(m.group(1))]
    season_numbers = [s["season_number"] for s in seasons]

    if skip_runtime:
        n_eps = sum(s.get("episode_count", 0) for s in seasons)
        avg_rt = None
    else:
        n_eps, avg_rt = season_stats(tid, season_numbers, key, today)
    if avg_rt is None:  # fallback: runtime list on the show itself
        rts = d.get("episode_run_time") or []
        avg_rt = round(sum(rts) / len(rts), 1) if rts else None

    genres = names(d.get("genres"))
    networks = names(d.get("networks"))
    companies = names(d.get("production_companies"))
    us = (d.get("watch/providers") or {}).get("results", {}).get("US", {})
    streaming = names(us.get("flatrate"))

    last_air_year = str(d.get("last_air_date") or "")[:4]
    if row["status_per_nyt"] == "ended" and not scope.startswith("season_") \
            and last_air_year and last_air_year != str(row["end_year"]).replace(".0", ""):
        reasons.append(f"last air year {last_air_year} differs from NYT end year")
    for field, val in (("genres", genres), ("networks", networks), ("runtime", avg_rt),
                       ("imdb_id", (d.get("external_ids") or {}).get("imdb_id"))):
        if not val:
            reasons.append(f"missing {field}")

    show = {
        "tmdb_id": tid,
        "tmdb_match": quality,
        "tmdb_name": d.get("name"),
        "tmdb_type": d.get("type"),
        "tmdb_status": d.get("status"),
        "tmdb_first_air_date": d.get("first_air_date"),
        "tmdb_last_air_date": d.get("last_air_date"),
        "seasons_analyzed": len(seasons),
        "episodes_analyzed": n_eps,
        "avg_episode_runtime_min": avg_rt,
        "est_total_runtime_hours": round(avg_rt * n_eps / 60, 1) if avg_rt and n_eps else None,
        "origin_country": "|".join(d.get("origin_country") or []),
        "original_language": d.get("original_language"),
        "imdb_id": (d.get("external_ids") or {}).get("imdb_id"),
        "tmdb_vote_average": d.get("vote_average"),
        "tmdb_vote_count": d.get("vote_count"),
        "genres": "|".join(genres),
        "networks": "|".join(networks),
        "production_companies": "|".join(companies),
        "streaming_us": "|".join(streaming),
        "collected_date": today,
    }
    return show, genres, networks, companies, streaming, reasons

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="only process the first N shows (test)")
    parser.add_argument("--skip-runtime", action="store_true",
                        help="skip per-season requests (faster; no runtime data)")
    args = parser.parse_args()

    key = get_key()
    base = pd.read_csv(RAW_FILE)
    if args.limit:
        base = base.head(args.limit)

    overrides = {}
    if OVERRIDES_FILE.exists():
        ov = pd.read_csv(OVERRIDES_FILE)
        overrides = dict(zip(ov["nyt_rank"].astype(int), ov["tmdb_id"]))

    today = date.today().isoformat()
    shows, genres_rows, net_rows, co_rows, st_rows, review = [], [], [], [], [], []

    for _, row in base.iterrows():
        rank = int(row["nyt_rank"])
        print(f"[{rank:>3}/100] {row['title']} ...", flush=True)
        try:
            show, g, n, c, s, reasons = collect_one(
                row, key, overrides, args.skip_runtime, today)
        except Exception as exc:  # keep going if one show fails
            show, g, n, c, s, reasons = {}, [], [], [], [], [f"error: {exc}"]
        shows.append({**row.to_dict(), **show})
        genres_rows += [{"nyt_rank": rank, "genre": x} for x in g]
        net_rows += [{"nyt_rank": rank, "network": x, "position": i + 1} for i, x in enumerate(n)]
        co_rows += [{"nyt_rank": rank, "company": x} for x in c]
        st_rows += [{"nyt_rank": rank, "platform": x, "country": "US", "checked_date": today} for x in s]
        if reasons:
            review.append({"nyt_rank": rank, "title": row["title"],
                           "tmdb_id": show.get("tmdb_id"), "reasons": "; ".join(reasons)})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(shows).to_csv(OUT_DIR / "shows_tmdb.csv", index=False, encoding="utf-8")
    pd.DataFrame(genres_rows, columns=["nyt_rank", "genre"]).to_csv(OUT_DIR / "show_genres.csv", index=False)
    pd.DataFrame(net_rows, columns=["nyt_rank", "network", "position"]).to_csv(OUT_DIR / "show_networks.csv", index=False)
    pd.DataFrame(co_rows, columns=["nyt_rank", "company"]).to_csv(OUT_DIR / "show_companies.csv", index=False)
    pd.DataFrame(st_rows, columns=["nyt_rank", "platform", "country", "checked_date"]).to_csv(
        OUT_DIR / "show_streaming_us.csv", index=False)
    pd.DataFrame(review, columns=["nyt_rank", "title", "tmdb_id", "reasons"]).to_csv(
        OUT_DIR / "review_needed.csv", index=False)

    print(f"\nDone. {len(shows)} shows processed, {len(review)} need a manual check.")
    print(f"Files saved in {OUT_DIR}")


if __name__ == "__main__":
    main()



