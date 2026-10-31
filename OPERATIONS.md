# The Goss Room Operations

The live site is built in `/home/ubuntu/web/thegossroom` on Harold and deployed
to Cloudflare Pages by `harold_run.py`. GitHub is a source backup; the live
directory is currently not a Git worktree.

## Lifecycle

- Status: `cd /home/ubuntu/web/thegossroom && python3 harold_run.py --status`
- One safe rebuild/deploy: `cd /home/ubuntu/web/thegossroom && python3 harold_run.py --build`
- Full manual pipeline: `cd /home/ubuntu/web/thegossroom && python3 harold_run.py --full`
- Restart: there is no persistent TGR service. Allow the current locked run to
  finish, then run the required command above. Overlapping runs stop safely on
  `.harold_run.lock`.
- Stop scheduling: edit the `ubuntu` crontab and comment only the four TGR
  entries (`--scrape`, `--post`, `--weekly`, and `--monthly`). Do not stop the
  system cron daemon because it owns unrelated Harold jobs.
- Start scheduling: restore those same four entries with the documented
  15-minute, hourly, weekly, and monthly schedules in `harold_run.py`.

## Logs and dependencies

- Pipeline log: `/home/ubuntu/web/thegossroom/harold.log`
- Generated site: `/home/ubuntu/web/thegossroom/_site`
- Retained content: `_posts`, `_archive`, and `_cold_storage`
- Recovery artifact: `recovery-index.json`; it is rebuilt before every Jekyll
  build and maps retained removed URLs to the strongest live tag match.
- External dependencies: RSS publishers, Python 3 with PyYAML, the bundled Ruby
  environment and Jekyll, Wrangler, Cloudflare Pages credentials in `.env`, and
  Bluesky credentials for the separate posting phase.

## First checks on failure

1. Run `python3 harold_run.py --status` and inspect the last 100 lines of
   `harold.log` without printing `.env`.
2. Run `python3 scripts/build_recovery_index.py` and confirm it reports live and
   removed routes with no unexpected malformed-file spike.
3. Run the recovery regression tests with
   `python3 -m unittest scripts/test_build_recovery_index.py -v`.
4. Run `python3 harold_run.py --build`; a failed index or Jekyll build must stop
   before Cloudflare deployment.
5. Check a known removed URL, `/recovery-index.json`, and a current article from
   outside Harold. The removed URL should briefly say it is matching a related
   story and then navigate to a live article.

## Rollback

Each manual production repair must first copy replaced files into a timestamped
directory under `/home/ubuntu/backups/thegossroom/`. Restore only those files,
run the unit tests, then use `python3 harold_run.py --build` to republish.
