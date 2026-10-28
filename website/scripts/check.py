"""Check publication integrity, local links and agreement with the imported evidence."""
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from build import ROOT, SOURCE, OUT, expand_source


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.text = [], [], []
        self.tables = self.headings = self.equations = 0
        self.heading_levels = []
        self.hidden_depth = 0
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag in {"style", "script"}:
            self.hidden_depth += 1
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for field in ("href", "src"):
            if attrs.get(field):
                self.links.append(attrs[field])
        self.tables += tag == "table"
        self.headings += tag in {"h2", "h3", "h4"}
        if tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.heading_levels.append(int(tag[1]))
        self.equations += "equation" in attrs.get("class", "").split()

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.hidden_depth -= 1

    def handle_data(self, text):
        if not self.hidden_depth:
            self.text.append(text)


def words(value):
    return ' '.join(re.findall(r"[a-z0-9]+", value.lower()))


def main():
    errors, checks = [], []
    pages = {}
    for path in OUT.rglob("*.html"):
        raw = path.read_text(encoding="utf-8")
        page = Page(raw)
        pages[path.resolve()] = page
        duplicates = [key for key, count in Counter(page.ids).items() if count > 1]
        errors.extend(f"Duplicate anchor {key}: {path}" for key in duplicates)
        if any(second > first + 1 for first, second in zip(page.heading_levels, page.heading_levels[1:])):
            errors.append('Skipped heading level in ' + str(path))
        if any(token in raw for token in ["{{", "ASTRAHTMLTOKEN", "REFERENCESPOSITION", "authors and affiliations", r"\caseframe", r"\begin{"]):
            errors.append("Unconverted markup in " + str(path))
    for path, page in pages.items():
        for url in page.links:
            link = urlsplit(url)
            if link.scheme or link.netloc:
                continue
            target = (path.parent / unquote(link.path)).resolve() if link.path else path
            if target.is_dir():
                target /= "index.html"
            if not target.exists():
                errors.append(f"Missing asset: {path.name} -> {url}")
            elif link.fragment and target.suffix == '.html' and unquote(link.fragment) not in pages[target].ids:
                errors.append(f"Broken anchor: {url}")
    checks.append("All local assets and cross-page anchors")
    report = pages[(OUT / "report/index.html").resolve()]
    inventory = json.loads((ROOT / "content/report-inventory.json").read_text(encoding="utf-8"))
    for key, actual, expected in [("tables", report.tables, inventory["tables"]), ("headings", report.headings, len(inventory["headings"])+2), ("equations", report.equations, inventory["equations"])]:
        if actual != expected:
            errors.append(f"Report {key}: expected {expected}, got {actual}")
    report_text = words(' '.join(report.text))
    # Independently scan continuous prose in the original, before export normalization.
    prose = re.sub(r"\\(?:citepending|citep|ref|label|includegraphics)(?:\[[^]]*\])?\{[^}]*\}", "|", expand_source())
    prose = re.sub(r"\\[A-Za-z]+\*?", "|", prose)
    runs = re.findall(r"[A-Za-z0-9][A-Za-z0-9\s.,;:!?“”'’()–—\-+/]*", prose)
    verified = 0
    for run in runs:
        normalized = words(run)
        if len(normalized.split()) >= 8:
            if normalized not in report_text:
                errors.append("Missing source prose: " + run.strip()[:220])
            else:
                verified += 1
    checks.append(f"{verified} original prose spans (8+ words), captions included")
    source_data = json.loads((SOURCE / 'figures/task_comparison_data.json').read_text())
    served_data = json.loads((OUT / 'assets/results.json').read_text())
    if source_data['series'] != served_data['series']:
        errors.append('Result series changed')
    successes = sum(rate / 100 * 50 for rate in served_data['series']['Our harness'])
    if successes != 777:
        errors.append(f'Incorrect successes: {successes}')
    appendix = (SOURCE / 'sections/appendix.tex').read_text()
    for task, rate in zip(source_data['tasks'], source_data['series']['Our harness']):
        if not re.search(re.escape(task) + r'\s*&\s*' + re.escape(f'{rate:.1f}') + r'\s*&', appendix):
            errors.append('Result not found in original task table: ' + task)
    checks.append('All 16 task rates agree with source table; 777/800 successes')
    videos = json.loads((OUT / 'assets/videos.json').read_text())
    for item in videos:
        for chapter in item['chapters']:
            if not 0 <= chapter['time'] < item['duration']:
                errors.append('Invalid chapter: ' + item['slug'])
        if abs(item['duration'] - item['frames']/item['fps']) > .001:
            errors.append('Invalid playback accounting: ' + item['slug'])
    checks.append('Four video chapter timelines within recorded playback durations')
    result = {"checks": checks, "errors": errors}
    (ROOT / ".cache").mkdir(parents=True, exist_ok=True)
    (ROOT / '.cache/check-results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
