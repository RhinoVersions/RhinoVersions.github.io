#!/usr/bin/env python3
"""Generate static, crawlable pages for every Rhino build in the version data.

The dashboard (index.html) builds its version list in the browser, so search
engines only ever see an empty shell and a search such as
`rhino "8.17.25066.07002" download` never matches this site. This script turns
data/rhino-versions-all.md into plain HTML pages that need no JavaScript:

    rhino/index.html                  overview of every major version
    rhino/<major>/index.html          every build of one major, e.g. rhino/8/
    rhino/<major>/<build>/index.html  one build, e.g. rhino/8/8.17.25066/
    sitemap.xml                       all of the above plus the dashboard

Builds are grouped the way the dashboard groups them (major.minor.yyddd), so a
build page names both its Windows (...07001) and its Mac (...07002) version.
The output is deterministic and pages of builds that left the data are
removed, so it is safe to rerun after every data update:

    python scripts/generate_pages.py
"""
import argparse
import datetime as dt
import html
import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

SITE_URL = "https://rhinoversions.github.io"
SITE_NAME = "Rhino Versions"
# Every index.html below this directory is generated (and pruned) by this script.
OUTPUT_DIR = "rhino"
# Keep in sync with the ?v= cache-busting query strings in index.html.
ASSET_VERSION = "20261006"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_ALL = os.getenv("MD_PATH_ALL", "data/rhino-versions-all.md")
# Majors that ship only as prerelease (WIP/Beta) builds, as in fetch_versions.py.
PRERELEASE_MAJORS = {
    t for t in re.split(r"[,\s]+", os.getenv("RHINO_PRERELEASE_MAJORS", "9").strip()) if t
}

LINK_RE = re.compile(r"- \[([^\]]+)\]\(([^)]+)\)")
INSTALLER_RE = re.compile(r"^(.+)\.(exe|dmg)$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

# Installer languages in display order; "multi" marks multilingual installers.
LOCALE_NAMES = {
    "multi": "Multilingual",
    "en-us": "English (US)",
    "de-de": "German (Deutsch)",
    "es-es": "Spanish (Español)",
    "fr-fr": "French (Français)",
    "it-it": "Italian (Italiano)",
    "ja-jp": "Japanese (日本語)",
    "ko-kr": "Korean (한국어)",
    "zh-cn": "Chinese, Simplified (简体中文)",
    "zh-tw": "Chinese, Traditional (繁體中文)",
}
LOCALE_ORDER = {loc: i for i, loc in enumerate(LOCALE_NAMES)}

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# Same platform icons as the dashboard (assets/js/script.js).
WINDOWS_ICON = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="flex-shrink:0" aria-hidden="true">'
    '<path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-13.051-1.8z"/></svg>'
)
MAC_ICON = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="flex-shrink:0" aria-hidden="true">'
    '<path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53'
    'C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98'
    '-.22.15-2.19 1.28-2.17 3.83.03 3.02 2.65 4.03 2.68 4.04l-.06.2M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19'
    '-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>'
)


def esc(value) -> str:
    """Escape text for use in HTML content and quoted attributes."""
    return html.escape(str(value), quote=True)


# ============================================
# Data
# ============================================

@dataclass(frozen=True)
class Installer:
    filename: str
    url: str
    platform: str  # "windows" or "mac"
    locale: str    # e.g. "en-us", or "multi" for a multilingual installer
    version: str   # e.g. "8.17.25066.07001"


@dataclass
class Build:
    """All installers of one build, keyed like the dashboard: major.minor.yyddd."""
    key: str
    windows: List[Installer] = field(default_factory=list)
    mac: List[Installer] = field(default_factory=list)

    @property
    def major(self) -> str:
        return self.key.split(".")[0]

    @property
    def minor(self) -> str:
        return self.key.split(".")[1]

    @property
    def date(self) -> dt.date:
        return decode_build_date(self.key.split(".")[2])

    @property
    def windows_version(self) -> Optional[str]:
        return self.windows[0].version if self.windows else None

    @property
    def mac_version(self) -> Optional[str]:
        return self.mac[0].version if self.mac else None

    @property
    def is_prerelease(self) -> bool:
        return self.major in PRERELEASE_MAJORS

    @property
    def path(self) -> str:
        return f"/{OUTPUT_DIR}/{self.major}/{self.key}/"


def version_tuple(version: str) -> Tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


def build_key(version: str) -> str:
    """major.minor.yyddd, the build's day (getVersionBuildKey in script.js).

    Unites a build's Windows exe with its Mac dmg, whose last digits differ.
    """
    return ".".join(version.split(".")[:3])


def decode_build_date(yyddd: str) -> dt.date:
    """Rhino encodes the build date as yyddd: 25066 = day 66 of 2025."""
    return dt.date(2000 + int(yyddd[:-3]), 1, 1) + dt.timedelta(days=int(yyddd[-3:]) - 1)


def nuget_version(version: str) -> str:
    """NuGet normalizes away leading zeros: 8.17.25066.07001 -> 8.17.25066.7001."""
    return ".".join(str(int(p)) for p in version.split("."))


def parse_installer(filename: str, url: str) -> Optional[Installer]:
    """Parse an installer filename like parseVersionFromFilename in script.js.

    rhino_en-us_8.17.25066.07001.exe -> Windows, en-us
    rhino_9.0.26272.12303.exe        -> Windows, multilingual (prerelease)
    rhino_8.17.25066.07002.dmg       -> Mac, multilingual
    rhino_wip_9.0.26167.11546.dmg    -> Mac, multilingual (prerelease)
    """
    match = INSTALLER_RE.match(filename)
    if not match or not url.startswith(("https://", "http://")):
        return None
    parts = match.group(1).split("_")
    if len(parts) == 3:
        locale = "multi" if parts[1] == "wip" else parts[1]
    elif len(parts) == 2:
        locale = "multi"
    else:
        return None
    version = parts[-1]
    if not VERSION_RE.match(version):
        return None
    platform = "windows" if match.group(2) == "exe" else "mac"
    return Installer(filename, url, platform, locale, version)


def load_builds(markdown: str) -> List[Build]:
    """Group the installers listed in a data file into builds, newest first."""
    builds: Dict[str, Build] = {}
    for filename, url in LINK_RE.findall(markdown):
        installer = parse_installer(filename, url)
        if installer is None:
            continue
        key = build_key(installer.version)
        build = builds.setdefault(key, Build(key))
        group = build.windows if installer.platform == "windows" else build.mac
        # Like the dashboard, keep only the newest installer per language.
        for i, existing in enumerate(group):
            if existing.locale == installer.locale:
                if version_tuple(installer.version) > version_tuple(existing.version):
                    group[i] = installer
                break
        else:
            group.append(installer)

    def locale_key(installer: Installer) -> Tuple[int, str]:
        return (LOCALE_ORDER.get(installer.locale, len(LOCALE_ORDER)), installer.locale)

    for build in builds.values():
        build.windows.sort(key=locale_key)
        build.mac.sort(key=locale_key)
    return sorted(builds.values(), key=lambda b: version_tuple(b.key), reverse=True)


def builds_by_major(builds: Sequence[Build]) -> Dict[str, List[Build]]:
    """Builds per major, newest major first (builds keep their newest-first order)."""
    majors: Dict[str, List[Build]] = {}
    for build in sorted(builds, key=lambda b: version_tuple(b.key), reverse=True):
        majors.setdefault(build.major, []).append(build)
    return majors


# ============================================
# Wording
# ============================================

def long_date(d: dt.date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def short_date(d: dt.date) -> str:
    return f"{MONTHS[d.month - 1][:3]} {d.day}, {d.year}"


def major_name(major: str) -> str:
    """Rhino 8, or Rhino 9 Early Preview for prerelease-only majors."""
    return f"Rhino {major} Early Preview" if major in PRERELEASE_MAJORS else f"Rhino {major}"


def release_name(build: Build) -> str:
    """Short release name: SR17, Initial release or Early Preview."""
    if build.is_prerelease:
        return "Early Preview"
    if build.minor == "0":
        return "Initial release"
    return f"SR{build.minor}"


def release_label(build: Build) -> str:
    """Rhino 8 SR17, Rhino 8 initial release or Rhino 9 Early Preview."""
    if build.is_prerelease:
        return major_name(build.major)
    if build.minor == "0":
        return f"Rhino {build.major} initial release"
    return f"Rhino {build.major} SR{build.minor}"


def join_and(items: Sequence[str]) -> str:
    """a, b and c"""
    return " and ".join(filter(None, [", ".join(items[:-1]), items[-1]])) if items else ""


def platforms_text(build: Build) -> str:
    return " & ".join(name for name, items in (("Windows", build.windows), ("Mac", build.mac)) if items)


def build_title(build: Build) -> str:
    """Page title naming the exact version(s), e.g.

    Rhino 8.17.25066.07001 (Windows) & 8.17.25066.07002 (Mac) Download – Rhino 8 SR17
    """
    win, mac = build.windows_version, build.mac_version
    if win and mac and win != mac:
        versions = f"{win} (Windows) & {mac} (Mac) Download"
    else:
        versions = f"{win or mac} Download for {platforms_text(build)}"
    return f"Rhino {versions} – {release_label(build)}"


def windows_summary(build: Build) -> str:
    count = len(build.windows)
    if count > 1:
        return f"Windows installer {build.windows_version} in {count} languages"
    if build.windows[0].locale == "multi":
        return f"multilingual Windows installer {build.windows_version}"
    return f"Windows installer {build.windows_version}"


def build_summary(build: Build) -> str:
    parts = []
    if build.windows:
        parts.append(windows_summary(build))
    if build.mac:
        parts.append(f"Mac installer {build.mac_version}")
    return " and ".join(parts)


def build_description(build: Build) -> str:
    return (f"Download {release_label(build)} (build {build.key}, {long_date(build.date)}): "
            f"{build_summary(build)}, direct from McNeel.")


# ============================================
# HTML
# ============================================

def json_ld(data: dict) -> str:
    """Serialize structured data for a <script> block (no '</' breakouts)."""
    return json.dumps(data, ensure_ascii=False, indent=4).replace("</", "<\\/")


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in text.splitlines())


def render_page(*, title: str, description: str, path: str,
                crumbs: Sequence[Tuple[str, str]], main: str, majors: Sequence[str]) -> str:
    """Wrap a page's main content in the shared head, header and footer.

    `crumbs` are (name, path) pairs from the site root down to this page.
    """
    canonical = SITE_URL + path
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": SITE_URL + href}
            for i, (name, href) in enumerate(crumbs, start=1)
        ],
    }
    crumb_items = [f'<li><a href="{esc(href)}">{esc(name)}</a></li>' for name, href in crumbs[:-1]]
    crumb_items.append(f'<li aria-current="page">{esc(crumbs[-1][0])}</li>')
    archive_links = " · ".join(
        f'<a href="/{OUTPUT_DIR}/{esc(m)}/">{esc(major_name(m))}</a>' for m in majors
    )
    return f"""<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="canonical" href="{esc(canonical)}">
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">

    <meta property="og:type" content="website">
    <meta property="og:locale" content="en_US">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta property="og:url" content="{esc(canonical)}">
    <meta property="og:title" content="{esc(title)}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:image" content="{SITE_URL}/assets/img/logo.png">
    <meta property="og:image:alt" content="Rhino Versions Logo">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{esc(title)}">
    <meta name="twitter:description" content="{esc(description)}">
    <meta name="theme-color" content="#ffffff">

    <link rel="icon" type="image/png" sizes="any" href="/assets/img/logo.png">
    <link rel="apple-touch-icon" href="/assets/img/logo.png">
    <link rel="stylesheet" href="/assets/css/styles.css?v={ASSET_VERSION}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap"
        rel="stylesheet" crossorigin="anonymous">

    <script type="application/ld+json">
{indent(json_ld(breadcrumb_ld), 4)}
    </script>
    <!-- Same theme preference as the dashboard; prevents a flash of the wrong theme -->
    <script>
        (function () {{
            try {{
                var t = localStorage.getItem('theme') || 'system';
                var effective = t === 'system'
                    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
                    : t;
                document.documentElement.setAttribute('data-theme', effective);
                if (effective === 'dark') {{
                    document.querySelector('meta[name="theme-color"]').setAttribute('content', '#0d1117');
                }}
            }} catch (e) {{ }}
        }})();
    </script>
</head>

<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <header>
        <div class="container">
            <a href="/" class="header-brand">
                <img src="/assets/img/logo.png" alt="" aria-hidden="true" class="header-logo" width="28" height="28">
                <span class="header-title">{SITE_NAME}</span>
            </a>
            <nav class="header-nav" aria-label="Site">
                <a href="/">Dashboard</a>
                <a href="/{OUTPUT_DIR}/">All versions</a>
            </nav>
        </div>
    </header>

    <main id="main-content" class="container static-page" tabindex="-1">
        <nav class="breadcrumbs" aria-label="Breadcrumb">
            <ol>
{indent(chr(10).join(crumb_items), 16)}
            </ol>
        </nav>

{indent(main, 8)}
    </main>

    <footer>
        <div class="container">
            <nav aria-label="Version archive">
                <p class="footer-archive">Version archive: {archive_links} · <a href="/{OUTPUT_DIR}/">All versions</a></p>
            </nav>
            <p>Updated daily via <a href="https://github.com/rhinoversions/rhinoversions.github.io">GitHub Actions</a></p>
            <p class="footer-note">Data sourced from <a href="https://www.nuget.org/packages/RhinoCommon">NuGet RhinoCommon</a></p>
        </div>
    </footer>
</body>

</html>
"""


FINE_PRINT = (
    '<p class="fine-print">Installers are downloaded directly from McNeel\'s official download server '
    '(files.mcneel.com). Rhino is commercial software by Robert McNeel &amp; Associates and needs a '
    'license or evaluation to run. Build data comes from the '
    '<a href="https://www.nuget.org/packages/RhinoCommon">RhinoCommon</a> package on NuGet.</p>'
)


def installer_table(installers: Sequence[Installer]) -> str:
    rows = "\n".join(
        f'            <tr><td>{esc(LOCALE_NAMES.get(i.locale, i.locale))}</td>'
        f'<td><a href="{esc(i.url)}">{esc(i.filename)}</a></td></tr>'
        for i in installers
    )
    return f"""<div class="data-table-wrap">
    <table class="data-table">
        <thead><tr><th scope="col">Language</th><th scope="col">Installer</th></tr></thead>
        <tbody>
{rows}
        </tbody>
    </table>
</div>"""


def version_explainer(build: Build) -> str:
    """Spell out what this build's version number encodes."""
    major, minor, yyddd = build.key.split(".")
    day_of_year = int(yyddd[-3:])
    date_part = (f"{yyddd} is the build date: day {day_of_year} of {build.date.year}, "
                 f"{long_date(build.date)}")
    example = build.windows_version or build.mac_version
    if build.is_prerelease:
        meaning = f"{major} is the major version and {date_part}"
    elif minor == "0":
        meaning = f"{major} is the major version, {minor} marks the initial release and {date_part}"
    else:
        meaning = f"{major} is the major version, {minor} the service release (SR{minor}) and {date_part}"
    text = f"In {example}, {meaning}."
    if build.windows_version and build.mac_version and build.windows_version != build.mac_version:
        text += (f" The Mac build, {build.mac_version}, comes from the same day and differs from the "
                 f"Windows build {build.windows_version} only in its last digits.")
    return text


def render_build_page(build: Build, older: Optional[Build], newer: Optional[Build],
                      majors: Sequence[str]) -> str:
    label = release_label(build)
    win, mac = build.windows_version, build.mac_version

    h1_versions = " · ".join(
        f"{esc(v)} ({name})" for name, v in (("Windows", win), ("Mac", mac)) if v
    )
    if build.is_prerelease:
        kind = f"a {esc(major_name(build.major))} (WIP/Beta) build"
    elif build.minor == "0":
        kind = f"the initial release of Rhino {esc(build.major)}"
    else:
        kind = f"Rhino {esc(build.major)} Service Release {esc(build.minor)}"
    lede = (f"Build {esc(build.key)} is {kind}, built on "
            f'<time datetime="{build.date.isoformat()}">{long_date(build.date)}</time>. '
            f"Download the official {esc(build_summary(build))} directly from McNeel.")

    blocks = []
    if newer is None:
        badge_class = "latest-badge preview-badge" if build.is_prerelease else "latest-badge"
        blocks.append(f'<p class="{badge_class}">Latest {esc(major_name(build.major))} build</p>')
    blocks.append(f'<h1 class="page-title">{esc(label)} <span class="page-title-versions">{h1_versions}</span></h1>')
    blocks.append(f'<p class="page-lede">{lede}</p>')

    buttons = []
    if build.windows:
        primary = build.windows[0]
        lang = "" if primary.locale == "multi" else f", {LOCALE_NAMES.get(primary.locale, primary.locale)}"
        buttons.append(
            f'<a href="{esc(primary.url)}" class="download-btn cta-btn">{WINDOWS_ICON} Download for Windows'
            f'<span class="sr-only"> – Rhino {esc(win)}{esc(lang)}</span></a>')
    if build.mac:
        buttons.append(
            f'<a href="{esc(build.mac[0].url)}" class="download-btn cta-btn">{MAC_ICON} Download for Mac'
            f'<span class="sr-only"> – Rhino {esc(mac)}</span></a>')
    blocks.append('<div class="download-buttons static-cta">\n'
                  + indent("\n".join(buttons), 4) + "\n</div>")

    facts = [("Release", esc(label)),
             ("Build date", f'<time datetime="{build.date.isoformat()}">{long_date(build.date)}</time>')]
    if win:
        facts.append(("Windows version", esc(win)))
    if mac:
        facts.append(("Mac version", esc(mac)))
    if win and not build.is_prerelease:
        # Stable NuGet versions match the Windows build (prereleases add a -wip/-beta tag).
        nv = nuget_version(win)
        facts.append(("RhinoCommon on NuGet",
                      f'<a href="https://www.nuget.org/packages/RhinoCommon/{esc(nv)}">{esc(nv)}</a>'))
    blocks.append('<dl class="build-facts glass-card">\n'
                  + "\n".join(f"    <div><dt>{name}</dt><dd>{value}</dd></div>" for name, value in facts)
                  + "\n</dl>")

    for platform, version, installers in (("Windows", win, build.windows), ("Mac", mac, build.mac)):
        if installers:
            section_id = f"{platform.lower()}-installers"
            blocks.append(f'<section class="static-section" aria-labelledby="{section_id}">\n'
                          f'    <h2 id="{section_id}">Rhino {esc(version)} for {platform}</h2>\n'
                          f"{indent(installer_table(installers), 4)}\n</section>")
    blocks.append('<section class="static-section" aria-labelledby="version-number">\n'
                  '    <h2 id="version-number">About this version number</h2>\n'
                  f'    <p class="prose">{esc(version_explainer(build))}</p>\n</section>')

    pager = []
    if older:
        pager.append(f'<a href="{esc(older.path)}" class="pager-prev" rel="prev">'
                     f'<span class="pager-label">Older build</span>'
                     f'<span><span aria-hidden="true">← </span>{esc(release_label(older))} ({esc(older.key)})</span></a>')
    if newer:
        pager.append(f'<a href="{esc(newer.path)}" class="pager-next" rel="next">'
                     f'<span class="pager-label">Newer build</span>'
                     f'<span>{esc(release_label(newer))} ({esc(newer.key)})<span aria-hidden="true"> →</span></span></a>')
    if pager:
        blocks.append(f'<nav class="build-pager" aria-label="More {esc(major_name(build.major))} builds">\n'
                      + indent("\n".join(pager), 4) + "\n</nav>")

    blocks.append(f'<p class="static-links">See <a href="/{OUTPUT_DIR}/{esc(build.major)}/">all '
                  f'{esc(major_name(build.major))} versions</a> or '
                  f'<a href="/?version={esc(build.key)}">open this build in the dashboard</a>.</p>')
    blocks.append(FINE_PRINT)
    main = '<article class="build-page">\n' + indent("\n".join(blocks), 4) + "\n</article>"

    return render_page(
        title=build_title(build),
        description=build_description(build),
        path=build.path,
        crumbs=[(SITE_NAME, "/"), (f"Rhino {build.major}", f"/{OUTPUT_DIR}/{build.major}/"),
                (build.key, build.path)],
        main=main,
        majors=majors,
    )


def builds_table(builds: Sequence[Build]) -> str:
    rows = []
    for b in builds:
        win = (f'<a href="{esc(b.windows[0].url)}" title="Download Rhino {esc(b.windows_version)} for Windows">'
               f'{esc(b.windows_version)}</a>') if b.windows else '<span class="muted">—</span>'
        mac = (f'<a href="{esc(b.mac[0].url)}" title="Download Rhino {esc(b.mac_version)} for Mac">'
               f'{esc(b.mac_version)}</a>') if b.mac else '<span class="muted">—</span>'
        rows.append(
            f'            <tr><td><a href="{esc(b.path)}">{esc(b.key)}</a></td>'
            f'<td>{esc(release_name(b))}</td>'
            f'<td><time datetime="{b.date.isoformat()}">{short_date(b.date)}</time></td>'
            f"<td>{win}</td><td>{mac}</td></tr>")
    return f"""<div class="data-table-wrap">
    <table class="data-table">
        <thead><tr><th scope="col">Build</th><th scope="col">Release</th><th scope="col">Build date</th><th scope="col">Windows</th><th scope="col">Mac</th></tr></thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
    </table>
</div>"""


def render_major_page(major: str, builds: Sequence[Build], majors: Sequence[str]) -> str:
    name = major_name(major)
    newest, oldest = builds[0], builds[-1]
    platforms = "Windows and Mac" if any(b.mac for b in builds) else "Windows"
    count = f"{len(builds)} build{'s' if len(builds) != 1 else ''}"
    if major in PRERELEASE_MAJORS:
        title = f"All Rhino {major} WIP & Beta Builds – {name} Downloads for {platforms.replace(' and ', ' & ')}"
        h1 = f"{name} builds"
    else:
        title = f"All Rhino {major} Versions – Download Any Rhino {major} Build for {platforms.replace(' and ', ' & ')}"
        h1 = f"Rhino {major} versions"
    description = (f"Complete {name} version history: {count} from {oldest.key} ({long_date(oldest.date)}) "
                   f"to {newest.key} ({long_date(newest.date)}), with direct {platforms} installer "
                   f"downloads from McNeel.")
    lede = (f"All {count} of {esc(name)} published on NuGet, from {esc(oldest.key)} "
            f"({long_date(oldest.date)}) to {esc(newest.key)} ({long_date(newest.date)}). "
            f"Every build links to McNeel's official {platforms} installers.")
    latest = (f'Latest: <a href="{esc(newest.path)}">{esc(release_label(newest))} ({esc(newest.key)})</a> – '
              f'{esc(build_summary(newest))}, built {long_date(newest.date)}.')
    main = f"""<h1 class="page-title">{esc(h1)}</h1>
<p class="page-lede">{lede}</p>
<p class="latest-summary glass-card">{latest}</p>
<section class="static-section" aria-labelledby="all-builds">
    <h2 id="all-builds">All {esc(name)} builds</h2>
{indent(builds_table(builds), 4)}
</section>
{FINE_PRINT}"""
    return render_page(
        title=title,
        description=description,
        path=f"/{OUTPUT_DIR}/{major}/",
        crumbs=[(SITE_NAME, "/"), (f"Rhino {major}", f"/{OUTPUT_DIR}/{major}/")],
        main=main,
        majors=majors,
    )


def render_archive_page(by_major: Dict[str, List[Build]], builds: Sequence[Build]) -> str:
    majors = list(by_major)
    oldest = min(builds, key=lambda b: b.date)
    major_rows = "\n".join(
        f'                <tr><td><a href="/{OUTPUT_DIR}/{esc(m)}/">{esc(major_name(m))}</a></td>'
        f"<td>{len(bs)}</td>"
        f'<td><a href="{esc(bs[0].path)}">{esc(bs[0].key)}</a> ({esc(release_name(bs[0]))})</td>'
        f'<td><time datetime="{bs[0].date.isoformat()}">{short_date(bs[0].date)}</time></td></tr>'
        for m, bs in by_major.items()
    )
    recent = sorted(builds, key=lambda b: (b.date, version_tuple(b.key)), reverse=True)[:10]
    numbers = sorted(majors, key=int)
    names = join_and([f"Rhino {m}" for m in numbers])      # Rhino 6, Rhino 7, Rhino 8 and Rhino 9
    short = " & ".join(filter(None, [", ".join(numbers[:-1]), numbers[-1]]))  # 6, 7, 8 & 9
    main = f"""<h1 class="page-title">Rhino version archive</h1>
<p class="page-lede">{len(builds)} Rhino builds published on NuGet since {long_date(oldest.date)}, covering {esc(names)}. Every build links to McNeel's official Windows and Mac installers.</p>
<section class="static-section" aria-labelledby="majors">
    <h2 id="majors">Major versions</h2>
    <div class="data-table-wrap">
        <table class="data-table">
            <thead><tr><th scope="col">Version</th><th scope="col">Builds</th><th scope="col">Latest build</th><th scope="col">Build date</th></tr></thead>
            <tbody>
{major_rows}
            </tbody>
        </table>
    </div>
</section>
<section class="static-section" aria-labelledby="recent-builds">
    <h2 id="recent-builds">Recent builds</h2>
{indent(builds_table(recent), 4)}
</section>
{FINE_PRINT}"""
    return render_page(
        title=f"All Rhino Versions – Rhino {short} Download Archive",
        description=(f"Every Rhino build since {long_date(oldest.date)}: {len(builds)} versions of "
                     f"{names}, with direct Windows and Mac installer downloads from McNeel."),
        path=f"/{OUTPUT_DIR}/",
        crumbs=[(SITE_NAME, "/"), ("All versions", f"/{OUTPUT_DIR}/")],
        main=main,
        majors=majors,
    )


def render_sitemap(by_major: Dict[str, List[Build]], builds: Sequence[Build]) -> str:
    newest = max(b.date for b in builds)
    entries = [("/", newest), (f"/{OUTPUT_DIR}/", newest)]
    entries += [(f"/{OUTPUT_DIR}/{m}/", bs[0].date) for m, bs in by_major.items()]
    entries += [(b.path, b.date) for bs in by_major.values() for b in bs]
    urls = "\n".join(
        f"  <url>\n    <loc>{esc(SITE_URL + path)}</loc>\n    <lastmod>{d.isoformat()}</lastmod>\n  </url>"
        for path, d in entries
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}\n</urlset>\n")


def render_site(builds: Sequence[Build]) -> Dict[str, str]:
    """All generated files as {path relative to the site root: content}."""
    by_major = builds_by_major(builds)
    majors = list(by_major)
    files = {f"{OUTPUT_DIR}/index.html": render_archive_page(by_major, builds)}
    for major, major_builds in by_major.items():
        files[f"{OUTPUT_DIR}/{major}/index.html"] = render_major_page(major, major_builds, majors)
        for i, build in enumerate(major_builds):
            newer = major_builds[i - 1] if i > 0 else None
            older = major_builds[i + 1] if i + 1 < len(major_builds) else None
            files[build.path.strip("/") + "/index.html"] = render_build_page(build, older, newer, majors)
    files["sitemap.xml"] = render_sitemap(by_major, builds)
    return files


# ============================================
# Output
# ============================================

def write_site(root: str, files: Dict[str, str]) -> int:
    """Write the generated files and prune pages of builds that no longer exist.

    Only index.html files below OUTPUT_DIR are ever deleted. Returns the number
    of files created, changed or removed.
    """
    changed = 0
    for rel, content in files.items():
        path = os.path.join(root, *rel.split("/"))
        try:
            with open(path, encoding="utf-8") as fh:
                if fh.read() == content:
                    continue
        except FileNotFoundError:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        changed += 1

    expected = {os.path.normpath(os.path.join(root, *rel.split("/"))) for rel in files}
    out_dir = os.path.join(root, OUTPUT_DIR)
    for dirpath, _dirnames, filenames in os.walk(out_dir, topdown=False):
        if "index.html" in filenames:
            page = os.path.normpath(os.path.join(dirpath, "index.html"))
            if page not in expected:
                os.remove(page)
                changed += 1
        if dirpath != out_dir and not os.listdir(dirpath):
            os.rmdir(dirpath)
    return changed


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate static version pages and sitemap.xml")
    parser.add_argument("--data", default=os.path.join(REPO_ROOT, MD_ALL),
                        help="all-versions markdown file (default: %(default)s)")
    parser.add_argument("--root", default=REPO_ROOT,
                        help="site root to write into (default: %(default)s)")
    args = parser.parse_args(argv)

    with open(args.data, encoding="utf-8") as fh:
        builds = load_builds(fh.read())
    if not builds:
        # Never wipe every page because of an empty or broken data file.
        raise SystemExit(f"::error::No builds found in {args.data}; leaving generated pages untouched.")

    files = render_site(builds)
    changed = write_site(args.root, files)
    print(f"Generated {len(files)} files for {len(builds)} builds ({changed} written or removed).")


if __name__ == "__main__":
    main()
