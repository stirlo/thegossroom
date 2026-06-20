# TGR Scripts

Harold-native pipeline for The Gossip Room.

## Active scripts

| Script | Purpose | Frequency |
|--------|---------|-----------|
| `enhanced_gossip_scraper.py` | Scrape RSS feeds, score posts, update SQLite | Every 15 min |
| `bluesky_poster_enhanced.py` | Post hottest story to Bluesky (RSS dedup) | Hourly at :19 |
| `mega_archive.py` | Consolidate old posts into rich archive pages | Monthly |
| `manage_archive.py` | Move old posts out of active _posts/ | Weekly/Monthly |
| `memorial_cleanup.py` | Handle deceased celebrity records | Monthly |
| `tag_cleanup.py` | Clean/merge tags across posts | Weekly |
| `drama_temperature_calculator.py` | Batch temperature recalc (legacy, rarely needed) | Manual only |

## Orchestrator

`harold_run.py` (in repo root) is the single entry point for Harold's cron.

```
*/15 * * * *  python3 harold_run.py --scrape
19 * * * *    python3 harold_run.py --post
0 3 * * 0     python3 harold_run.py --weekly
0 4 1 * *     python3 harold_run.py --monthly
```

## Retired scripts

Legacy emergency tools from the GitHub Actions era are in `_retired/`.
Do not restore them — they write directly to celebrities.yml which is
now a read-only Jekyll snapshot. Harold SQLite is the source of truth.
