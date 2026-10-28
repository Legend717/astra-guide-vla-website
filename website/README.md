# Astra Guide VLA project website

This repository contains the website and its build sources. Controller code and
usage documentation are maintained in [astra-guide-vla](https://github.com/Legend717/astra-guide-vla).

Clone the website repository:

```sh
git clone https://github.com/Legend717/astra-guide-vla-website.git
cd astra-guide-vla-website
```

The project website includes the technical report, interactive diagrams, results,
and four demonstration videos. The generated site is in `docs/`.

## Preview

From the repository root, use Python 3.10 or newer:

```sh
python website/scripts/serve.py
```

Open <http://127.0.0.1:8765/>. Use `--port 8766` to choose another port.
The server also supports the `/astra-guide-vla-website/` prefix for testing project hosting.
Use the server rather than opening HTML files directly so video metadata loads correctly.

## Build

Edit the report in `website/report-source/`, the page templates in
`website/templates/`, and video chapter metadata in `website/content/videos.json`.
Building requires Pandoc 3.x. PDF generation also requires `latexmk`, pdfLaTeX,
and BibTeX.

```sh
python website/scripts/build.py
# Also regenerate the PDF:
python website/scripts/build.py --pdf
python website/scripts/check.py
```

Keep report tables and `website/report-source/figures/task_comparison_data.json`
in agreement when updating results. The checks cover report structure, prose,
task results, local assets, links, and video chapter times. Temporary build files
are stored in ignored `website/.cache/`.

The videos play at the recorded 20 fps and omit model inference waits; playback
duration is not end-to-end latency. The method animation illustrates scheduling
and does not measure speedup.

## Browser checks

```sh
node --check website/templates/site.js
```

With the preview server running, use an existing Playwright installation and browser:

```sh
node website/scripts/browser_check.cjs /path/to/playwright /path/to/browser
node website/scripts/mechanism_check.cjs /path/to/playwright /path/to/browser
```

Set `SITE_URL=http://127.0.0.1:8765/astra-guide-vla-website/` to test project-subpath hosting.

## Hosting

The `docs/` directory is a static site with no backend or build step required on
the host. For GitHub Pages, open **Settings > Pages**, select **Deploy from a branch**, then choose
**main** and **/docs** as the publishing source. No Actions workflow is required.
The expected project URL after enabling Pages is
<https://legend717.github.io/astra-guide-vla-website/>.

Commit website updates to `main`; keep generated `docs/` assets and their
`website/` sources together. This repository is maintained independently of the code repository.
