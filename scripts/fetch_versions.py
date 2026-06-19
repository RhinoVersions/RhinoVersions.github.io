import argparse
import datetime as dt
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Iterable, Tuple, Union
from urllib.parse import urlparse
import requests

# Configuration
USER_AGENT = "nuget-rhino-actions/1.5"
REG_INDEX = "https://api.nuget.org/v3/registration5-semver1/rhinocommon/index.json"
MAC_RELEASE_URL_TEMPLATE = "https://files.mcneel.com/rhino/{major}/mac/releases/{filename}"
STABLE_SUFFIX_RE = re.compile(r'^[0-9]+(\.[0-9]+){3}$')  # e.g., 8.24.25281.15001
# Prerelease, e.g. 9.0.26097.12305-wip (Rhino 9 is WIP-only on NuGet).
PRERELEASE_SUFFIX_RE = re.compile(r'^[0-9]+(\.[0-9]+){3}-[0-9A-Za-z.]+$')
BULLET_RE = re.compile(r'^\s{4}- \[.*\]\(.*\)\s*$')

# Environment variables with defaults
MAJORS_RAW = os.getenv("RHINO_MAJORS", "6,7,8,9")
# Majors for which we also accept prerelease (-wip/-beta/...) builds.
# Rhino 9 currently ships only as WIP prereleases on NuGet.
PRERELEASE_MAJORS_RAW = os.getenv("RHINO_PRERELEASE_MAJORS", "9")
LOCALES_RAW = os.getenv("RHINO_LOCALES", "en-us,de-de,es-es,fr-fr,it-it,ja-jp,ko-kr,zh-cn,zh-tw")
MD_LATEST = os.getenv("MD_PATH", "data/rhino-versions.md")
MD_ALL = os.getenv("MD_PATH_ALL", "data/rhino-versions-all.md")
HEAD_CHECK_LATEST = os.getenv("HEAD_CHECK_LATEST", "true").lower() == "true"

# Parse lists
tokens = [t for t in re.split(r'[,\s]+', MAJORS_RAW.strip()) if t]
MAJORS: List[Union[int, str]] = []
for t in tokens:
    try:
        MAJORS.append(int(t))
    except ValueError:
        MAJORS.append(t)

LOCALES = [loc.strip() for loc in re.split(r'[,\s]+', LOCALES_RAW.strip()) if loc.strip()]

PRERELEASE_MAJORS = {t for t in re.split(r'[,\s]+', PRERELEASE_MAJORS_RAW.strip()) if t}


def is_prerelease(ver: str) -> bool:
    """True if the version carries a prerelease suffix, e.g. 9.0.26097.12305-wip."""
    return "-" in ver


def fetch_registration_index() -> dict:
    """Fetch the NuGet registration index for RhinoCommon."""
    print(f"Fetching {REG_INDEX}...")
    r = requests.get(REG_INDEX, timeout=30, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.json()


def versions_from_registration(reg_json: dict) -> List[str]:
    """Extract all versions from the registration index."""
    pages = reg_json.get("items", [])

    def get_items_from_page(page: dict) -> List[dict]:
        items = page.get("items")
        if items is not None:
            return items

        page_url = page.get("@id")
        if not page_url:
            return []

        print(f"Fetching page: {page_url}")
        pr = requests.get(page_url, timeout=30, headers={"User-Agent": USER_AGENT})
        pr.raise_for_status()
        return pr.json().get("items", [])

    # Fetch pages concurrently while maintaining order
    with ThreadPoolExecutor(max_workers=10) as executor:
        pages_items = list(executor.map(get_items_from_page, pages))

    versions = []
    for items in pages_items:
        for leaf in items:
            ver = (leaf.get("catalogEntry") or {}).get("version")
            if ver:
                versions.append(ver)
    return versions


def parse_version_tuple(ver: str) -> Tuple[int, ...]:
    """Parse version string into a tuple of integers (ignoring any -prerelease suffix)."""
    core = ver.split("-", 1)[0]
    parts = core.split(".")
    return tuple(int(p) for p in parts[:4])


def list_stable_for_majors(all_versions: List[str], majors: Iterable[Union[int, str]]) -> List[str]:
    """Filter for matching major versions.

    Accepts stable 4-part versions for all requested majors, plus prerelease
    builds (e.g. 9.0.26097.12305-wip) for majors listed in PRERELEASE_MAJORS.
    """
    majors_set = {str(m) for m in majors}
    prefixes = tuple(f"{m}." for m in majors_set)
    cands = []
    for v in all_versions:
        # Optimization: fast pre-filter on the major prefix.
        if not v.startswith(prefixes):
            continue
        major = v.split(".", 1)[0]
        if major not in majors_set:
            continue
        if STABLE_SUFFIX_RE.match(v):
            cands.append(v)
        elif major in PRERELEASE_MAJORS and PRERELEASE_SUFFIX_RE.match(v):
            cands.append(v)
    cands.sort(key=parse_version_tuple, reverse=True)
    return cands


def decode_version_date(ver: str) -> dt.date:
    """Decode the date from the version string (Rhino versioning scheme)."""
    # Rhino VersionNumber: major.minor.yyddd.hhmmb
    try:
        yyddd = ver.split(".")[2]
        yy = int(yyddd[:-3])
        ddd = int(yyddd[-3:])
        year = 2000 + yy
        return dt.date(year, 1, 1) + dt.timedelta(days=ddd - 1)
    except (IndexError, ValueError):
        # Fallback for unexpected formats
        return dt.date.today()


def _version_for_filename(ver: str) -> str:
    """Normalize version string for filenames (pad to 5 digits).

    Any prerelease suffix is dropped: the actual installer for 9.0.26097.12305-wip
    is published as rhino_..._9.0.26097.12305.exe (no -wip).
    """
    parts = ver.split("-", 1)[0].split(".")
    if len(parts) < 4:
        raise ValueError(f"Unexpected version: {ver}")
    parts[2] = parts[2].zfill(5)  # yyddd
    parts[3] = parts[3].zfill(5)  # hhmmb
    return ".".join(parts[:4])


def build_windows_url(ver: str, date_obj: dt.date, locale: str) -> str:
    """Build the Windows download URL."""
    ver_name = _version_for_filename(ver)
    ymd = date_obj.strftime("%Y%m%d")
    filename = f"rhino_{locale}_{ver_name}.exe"
    return f"https://files.mcneel.com/dujour/exe/{ymd}/{filename}"


def build_windows_url_candidates(ver: str, date_obj: dt.date, locale: str) -> List[str]:
    """Windows installer URL candidates for a build.

    WIP/prerelease installers are a single multilingual exe with no locale segment
    (rhino_<ver>.exe). Older WIP builds used a locale segment (rhino_<locale>_<ver>.exe).
    Returns both so the caller can HEAD-check and pick the one that exists.
    """
    ver_name = _version_for_filename(ver)
    ymd = date_obj.strftime("%Y%m%d")
    base = f"https://files.mcneel.com/dujour/exe/{ymd}"
    return [
        f"{base}/rhino_{ver_name}.exe",            # multilingual (current WIP convention)
        f"{base}/rhino_{locale}_{ver_name}.exe",   # locale-specific (older WIP / stable)
    ]


def build_mac_url_candidates(ver: str) -> List[str]:
    """
    Build candidate Mac download URLs.
    Mac versions often match the Windows version exactly, OR have the last digit incremented by 1.
    e.g. Windows ...15001 -> Mac ...15002
    """
    candidates = []
    ver_name = _version_for_filename(ver)
    major = ver.split(".")[0]
    
    # Candidate 1: Exact match
    filename1 = f"rhino_{ver_name}.dmg"
    url1 = MAC_RELEASE_URL_TEMPLATE.format(major=major, filename=filename1)
    candidates.append(url1)
    
    # Candidate 2: Last digit + 1
    try:
        parts = ver_name.split(".")
        last_part = int(parts[3])
        new_last_part = str(last_part + 1).zfill(5)
        parts[3] = new_last_part
        ver_name_plus1 = ".".join(parts)
        filename2 = f"rhino_{ver_name_plus1}.dmg"
        url2 = MAC_RELEASE_URL_TEMPLATE.format(major=major, filename=filename2)
        candidates.append(url2)
    except ValueError:
        pass
        
    return candidates


def url_exists(url: str) -> bool:
    """Check if a URL exists (HEAD request)."""
    try:
        r = requests.head(url, timeout=10, allow_redirects=True, headers={"User-Agent": USER_AGENT})
        if r.status_code == 200:
            return True
        # Some servers might block HEAD or return 405, try GET with stream
        if r.status_code in (405, 403):
            r = requests.get(url, timeout=10, stream=True, allow_redirects=True, headers={"User-Agent": USER_AGENT})
            r.close()
            return r.status_code == 200
        return False
    except requests.RequestException:
        return False


def resolve_mac_url(ver: str) -> Union[str, None]:
    """Return the first reachable Mac DMG URL for a build, or None.

    Mac filenames are not 1:1 with the Windows build number (often last digit +1),
    and many builds have no Mac DMG at all (e.g. early Rhino 6, all WIP builds).
    HEAD-check candidates so we only ever emit links that actually exist.
    """
    for cand in build_mac_url_candidates(ver):
        if url_exists(cand):
            return cand
    return None


def resolve_mac_urls(versions: List[str], max_workers: int = 16) -> dict:
    """Resolve verified Mac URLs for many builds concurrently.

    Returns {version: url} only for builds whose Mac DMG was found.
    """
    result = {}
    if not versions:
        return result
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for ver, url in zip(versions, executor.map(resolve_mac_url, versions)):
            if url:
                result[ver] = url
    return result


def resolve_prerelease_windows_url(ver: str) -> Union[str, None]:
    """Return the first reachable Windows installer URL for a prerelease build.

    WIP installer filename conventions vary (multilingual rhino_<ver>.exe for newer
    builds, locale-specific rhino_en-us_<ver>.exe for older), so HEAD-check candidates.
    """
    d = decode_version_date(ver)
    for cand in build_windows_url_candidates(ver, d, "en-us"):
        if url_exists(cand):
            return cand
    return None


def resolve_prerelease_windows_urls(versions: List[str], max_workers: int = 16) -> dict:
    """Resolve verified Windows URLs for prerelease builds concurrently.

    Returns {version: url} only for builds whose installer was found.
    """
    result = {}
    if not versions:
        return result
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for ver, url in zip(versions, executor.map(resolve_prerelease_windows_url, versions)):
            if url:
                result[ver] = url
    return result


def windows_installer_exists(ver: str) -> bool:
    """True if the en-us Windows installer for a build is reachable.

    Used as a cheap proxy for "this build has a published Windows installer":
    a handful of NuGet entries (e.g. ancient 2016 Rhino 6 builds) have no exe
    on the CDN, and McNeel publishes all locales of a build together.
    """
    return url_exists(build_windows_url(ver, decode_version_date(ver), "en-us"))


def resolve_live_windows(versions: List[str], max_workers: int = 16) -> set:
    """Return the subset of builds that have a reachable Windows installer."""
    live = set()
    if not versions:
        return live
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for ver, ok in zip(versions, executor.map(windows_installer_exists, versions)):
            if ok:
                live.add(ver)
    return live


def ensure_newline(s: str) -> str:
    return s if s.endswith("\n") else s + "\n"


def prepend_latest(md_path: str, filename: str, url: str) -> bool:
    """Prepend a new version to the latest versions file."""
    bullet = f"    - [{filename}]({url})"
    os.makedirs(os.path.dirname(md_path) or ".", exist_ok=True)

    if not os.path.exists(md_path):
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(bullet + "\n")
        print(f"[added:newfile] {bullet}")
        return True

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    if filename in content:
        # print("[ok] No update needed (already present).")
        return False

    lines = content.splitlines()
    insert_at = next((i for i, ln in enumerate(lines) if BULLET_RE.match(ln)), None)

    if insert_at is None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(bullet)
    else:
        lines.insert(insert_at, bullet)

    new_content = ensure_newline("\n".join(lines))
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[added] {bullet}")
    return True


def write_all(md_path_all: str, entries: List[Tuple[str, str]]) -> int:
    """Write all versions to the all-versions file."""
    os.makedirs(os.path.dirname(md_path_all) or ".", exist_ok=True)
    lines = [f"    - [{fn}]({u})" for (fn, u) in entries]
    with open(md_path_all, "w", encoding="utf-8") as f:
        f.write(ensure_newline("\n".join(lines)))
    return len(entries)


def get_stable_versions() -> List[str]:
    """Fetch all stable versions for configured majors from NuGet."""
    reg = fetch_registration_index()
    versions = versions_from_registration(reg)
    return list_stable_for_majors(versions, MAJORS)


def check_only():
    """Lightweight check: is the newest NuGet build for each major already in our data?

    Checks per-major (not just the single newest overall), so a fresh Rhino 9 WIP
    build triggers a rebuild even though stable Rhino 8 remains the latest release.
    """
    try:
        stable = get_stable_versions()

        if not stable:
            print("No versions found on NuGet.")
            _write_output("new_versions", "false")
            return

        # Newest build per major. `stable` is sorted descending, so the first
        # occurrence of each major is its newest build.
        latest_by_major = {}
        for v in stable:
            major = v.split(".", 1)[0]
            latest_by_major.setdefault(major, v)

        # We only need MD_ALL (the full history) to know whether a build is known;
        # MD_LATEST is a subset of it.
        content = ""
        if os.path.exists(MD_ALL):
            with open(MD_ALL, "r", encoding="utf-8") as f:
                content = f.read()

        new = False
        for major, v in sorted(latest_by_major.items()):
            ver_fn = _version_for_filename(v)
            present = ver_fn in content
            print(f"  Rhino {major}: latest {v} -> {'present' if present else 'MISSING'}")
            if not present:
                new = True

        if new:
            print("New version(s) detected! Full build required.")
            _write_output("new_versions", "true")
        else:
            print(f"All majors up to date in {MD_ALL}. Nothing to do.")
            _write_output("new_versions", "false")

    except Exception as e:
        print(f"::warning::NuGet check failed ({e}); skipping build to avoid cascading failure.")
        _write_output("new_versions", "false")


def _write_output(key: str, value: str):
    """Write a key=value pair to GITHUB_OUTPUT if available."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")
    print(f"  → {key}={value}")


def main():
    latest_version = None
    latest_date_iso = None
    latest_filename = None
    latest_url = None
    changed_latest = False
    all_count = 0

    try:
        # 1. Fetch available versions from NuGet
        stable = get_stable_versions()

        if not stable:
            print(f"::notice::No stable Rhino versions for majors: {', '.join(map(str, MAJORS))}.")
            all_count = write_all(MD_ALL, [])
        else:
            # 2. Build URLs for all versions
            all_entries_map = {}  # key: filename, value: url (to dedupe)
            
            # Cache for Mac URLs to avoid re-checking the same version multiple times
            # (though we iterate versions once, so simple dict is fine)
            
            print(f"Found {len(stable)} stable versions. Processing...")

            # Pre-resolve Mac DMG URLs for every non-prerelease build, in parallel.
            # Mac filenames don't track the Windows build number exactly (usually +1)
            # and older builds may have no Mac DMG, so each must be HEAD-checked.
            # Verifying ALL builds (not just the newest N) avoids emitting broken
            # links for older releases, which the previous top-N heuristic did.
            mac_targets = [v for v in stable if not is_prerelease(v)]
            print(f"Resolving Mac DMG URLs for {len(mac_targets)} builds...")
            mac_map = resolve_mac_urls(mac_targets)
            print(f"Found Mac DMGs for {len(mac_map)}/{len(mac_targets)} builds.")

            # Verify which stable builds actually have a Windows installer (a few
            # ancient NuGet entries do not), so we never emit dead exe links.
            print(f"Verifying Windows installers for {len(mac_targets)} builds...")
            win_live = resolve_live_windows(mac_targets)
            print(f"Found Windows installers for {len(win_live)}/{len(mac_targets)} builds.")

            # Pre-resolve prerelease (WIP) Windows installers concurrently too.
            pre_targets = [v for v in stable if is_prerelease(v)]
            pre_win_map = resolve_prerelease_windows_urls(pre_targets)
            if pre_targets:
                print(f"Found prerelease Windows installers for {len(pre_win_map)}/{len(pre_targets)} builds.")

            for v in stable:
                d = decode_version_date(v)

                # --- Prerelease (WIP): Windows-only, single multilingual installer ---
                # WIP builds (e.g. Rhino 9) ship one multilingual exe and no Mac DMG.
                # The exact filename convention changed over time, so HEAD-check
                # candidates and emit a single entry for whichever resolves.
                if is_prerelease(v):
                    win_url = pre_win_map.get(v)
                    if win_url:
                        fn = os.path.basename(urlparse(win_url).path)
                        all_entries_map[fn] = win_url
                    else:
                        print(f"[skip] No reachable Windows installer for prerelease {v}")
                    continue

                # --- Windows EXE (all locales) ---
                # McNeel publishes every locale of a build together, so emit all
                # locales for builds with a verified installer; skip dead builds.
                if v in win_live:
                    for locale in LOCALES:
                        u = build_windows_url(v, d, locale)
                        fn = os.path.basename(urlparse(u).path)
                        all_entries_map[fn] = u
                else:
                    print(f"[skip] No Windows installer published for {v}")

                # --- Mac DMG ---
                # Use the pre-resolved (HEAD-verified) Mac URL; absent for builds
                # with no published DMG (e.g. early Rhino 6).
                valid_mac_url = mac_map.get(v)
                if valid_mac_url:
                    fn = os.path.basename(urlparse(valid_mac_url).path)
                    all_entries_map[fn] = valid_mac_url

            # 3. Write all entries
            # Sort by version (descending), then by filename (to group locales)
            # Actually, the map keys are filenames.
            # We want to preserve the version order.
            # Filenames start with rhino_...
            # We want newest versions first.
            # Filenames contain version numbers, but sorting by string might be slightly off if padding differs (but we padded).
            # Let's sort by the version found in the filename.
            
            def sort_key(item):
                fn = item[0]
                # Extract version from filename to sort correctly
                # rhino_en-us_8.25.25328.11001.exe
                # rhino_8.25.25328.11002.dmg
                try:
                    # Remove extension
                    base = fn.rsplit('.', 1)[0]
                    parts = base.split('_')
                    ver_part = parts[-1] # 8.25.25328.11001
                    return parse_version_tuple(ver_part)
                except:
                    return (0,0,0,0)

            all_entries = sorted(all_entries_map.items(), key=sort_key, reverse=True)
            all_count = write_all(MD_ALL, all_entries)
            print(f"Wrote {all_count} entries to {MD_ALL}")

            # 4. Update Latest File (en-us only, both platforms)
            # The "Latest Release" hero shows the newest STABLE build only.
            # Prerelease (WIP) builds, e.g. Rhino 9, live in the version history
            # (MD_ALL) but never headline the latest card.
            v_latest = next((v for v in stable if not is_prerelease(v)), None)
            if v_latest:
                d_latest = decode_version_date(v_latest)
                
                # Windows Latest
                u_win = build_windows_url(v_latest, d_latest, "en-us")
                fn_win = os.path.basename(urlparse(u_win).path)
                
                if (not HEAD_CHECK_LATEST) or url_exists(u_win):
                    if prepend_latest(MD_LATEST, fn_win, u_win):
                        changed_latest = True
                    
                    # Set outputs for GitHub Actions (using Windows info)
                    latest_filename = fn_win
                    latest_url = u_win
                    latest_version = v_latest
                    latest_date_iso = d_latest.isoformat()
                else:
                    print(f"::warning::Latest Windows URL not reachable: {u_win}")

                # Mac Latest (already verified in the pre-resolved map)
                valid_mac_url = mac_map.get(v_latest)
                if valid_mac_url:
                    fn_mac = os.path.basename(urlparse(valid_mac_url).path)
                    if prepend_latest(MD_LATEST, fn_mac, valid_mac_url):
                        changed_latest = True
                else:
                    print(f"::warning::Could not find valid Mac URL for latest version {v_latest}")

    except Exception as e:
        print(f"::error::Failed: {e}")
        sys.exit(1)

    # 5. Summary & Outputs
    if latest_version:
        print(f"Latest version: {latest_version}")
        print(f"Build date:     {latest_date_iso}")
        print(f"Filename:       {latest_filename}")
        print(f"URL:            {latest_url}")
    print(f"All versions written: {all_count}")

    # GitHub Actions Output
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            if latest_version:  fh.write(f"version={latest_version}\n")
            if latest_date_iso: fh.write(f"date={latest_date_iso}\n")
            if latest_filename: fh.write(f"filename={latest_filename}\n")
            if latest_url:      fh.write(f"url={latest_url}\n")
            fh.write(f"all_count={all_count}\n")
            fh.write(f"changed={'true' if changed_latest else 'false'}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Rhino versions from NuGet")
    parser.add_argument("--check-only", action="store_true",
                        help="Only check if new versions exist, don't rebuild files")
    args = parser.parse_args()

    if args.check_only:
        check_only()
    else:
        main()
