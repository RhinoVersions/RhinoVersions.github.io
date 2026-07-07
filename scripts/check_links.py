#!/usr/bin/env python3
"""Verify that every download link in the version data files is reachable.

Used by the link-check GitHub Actions workflow, and runnable locally:

    python scripts/check_links.py data/rhino-versions.md data/rhino-versions-all.md

Exits non-zero if any link is unreachable after retries, printing the offenders.
Transient failures (timeouts, 5xx) are retried; definitive 4xx are reported
immediately. A byte-range GET is used (not just HEAD) so we detect files that
report 200 to HEAD but are actually gone.
"""
import argparse
import concurrent.futures
import datetime as dt
import json
import re
import sys
import time

import requests

USER_AGENT = "rhino-versions-linkcheck/1.0"
# Matches the URL inside a markdown link: - [text](URL)
LINK_RE = re.compile(r'\]\((https?://[^)]+)\)')
# 206 = partial content (our range request); 200 = host ignored the range.
OK_CODES = {200, 206}


def extract_urls(paths):
    """Collect the unique set of URLs across all given markdown files."""
    urls = set()
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            for match in LINK_RE.finditer(fh.read()):
                urls.add(match.group(1))
    return sorted(urls)


def check_url(url, timeout, retries):
    """Return (url, status, ok). Retries transient errors and 5xx."""
    last = None
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"},
                allow_redirects=True,
                timeout=timeout,
                stream=True,
            )
            resp.close()
            if resp.status_code in OK_CODES:
                return (url, resp.status_code, True)
            # 4xx is definitive (file genuinely missing) — don't waste retries.
            if resp.status_code < 500:
                return (url, resp.status_code, False)
            last = resp.status_code
        except requests.RequestException as exc:
            last = f"ERR:{type(exc).__name__}"
        # Back off before retrying a transient failure.
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
    return (url, last, False)


def main():
    parser = argparse.ArgumentParser(description="Check download links in markdown data files.")
    parser.add_argument("paths", nargs="+", help="Markdown files to scan for links.")
    parser.add_argument("--workers", type=int, default=48, help="Concurrent requests.")
    parser.add_argument("--timeout", type=int, default=60, help="Per-request timeout (s).")
    parser.add_argument("--retries", type=int, default=3, help="Attempts per URL.")
    parser.add_argument("--status-file", help="Write a JSON status summary to this path (online/total/checked_at).")
    args = parser.parse_args()

    urls = extract_urls(args.paths)
    print(f"Checking {len(urls)} unique links from {len(args.paths)} file(s)...")

    broken = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(check_url, u, args.timeout, args.retries) for u in urls]
        for future in concurrent.futures.as_completed(futures):
            url, status, ok = future.result()
            if not ok:
                broken.append((status, url))

    total = len(urls)
    ok_count = total - len(broken)
    print(f"\nResult: {ok_count}/{total} OK, {len(broken)} broken.")

    if args.status_file:
        status = {
            "online": ok_count,
            "total": total,
            "broken": len(broken),
            "checked_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(args.status_file, "w", encoding="utf-8") as fh:
            json.dump(status, fh, indent=2)
            fh.write("\n")
        print(f"Wrote status to {args.status_file}: {status}")

    if broken:
        print("\n::group::Broken links")
        for status, url in sorted(broken, key=lambda item: str(item[1])):
            print(f"  [{status}] {url}")
            print(f"::error::Broken link ({status}): {url}")
        print("::endgroup::")
        sys.exit(1)

    print("All links OK.")


if __name__ == "__main__":
    main()
