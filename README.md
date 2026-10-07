# Rhino Versions

A professional, automatically-updated dashboard for the latest Rhino 3D build downloads and version history.

🌐 **Live Site**: [rhinoversions.github.io](https://rhinoversions.github.io)

## How It Works

This repository uses **GitHub Actions** to automatically aggregate data from **NuGet RhinoCommon** packages daily. It validates download URLs and updates the static frontend hosted on **GitHub Pages**.

The dashboard renders its version list with JavaScript, so `scripts/generate_pages.py` also writes a plain-HTML page for every build (e.g. [`/rhino/8/8.17.25066/`](https://rhinoversions.github.io/rhino/8/8.17.25066/)), an index page per major version, and `sitemap.xml`. These pages carry the exact version numbers in their titles so search engines can index them; the daily workflow regenerates them whenever the data changes.

## Key Features

- **Daily Updates**: Build data reflects the latest NuGet releases.
- **Direct Downloads**: Immediate access to Windows and Mac installer builds.
- **Version History**: Comprehensive searchable history for Rhino 6, 7, 8, and 9 (Early preview).
- **Clean UI**: Minimalist, list-based dashboard inspired by official Rhino tooling.
- **Responsive**: Full mobile and touch-target support.

## Local Development

```bash
# Clone
git clone https://github.com/rhinoversions/rhinoversions.github.io.git
cd rhinoversions.github.io

# Run
python3 -m http.server 8000

# Regenerate the static version pages + sitemap after changing the data or the page template
python3 scripts/generate_pages.py
```

## Structure

- `.github/workflows/`: Automation logic for NuGet tracking.
- `scripts/`: Backend scripts (fetching versions, verification, static page generation).
- `data/`: Auto-generated markdown data files.
- `rhino/`, `sitemap.xml`: Auto-generated static version pages (do not edit by hand).
- `assets/`: Frontend resources (CSS, JS, Images).
- `index.html`: Main entry point.

## License

MIT License.

