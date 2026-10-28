"""Deterministic publication export. Requires Python 3.10+ and Pandoc 3.x."""
import argparse
import html
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "report-source"
OUT = ROOT.parent / "docs"
CACHE = ROOT / ".cache"
TITLE = "Can Astra Guide a VLA to Solve RoboMME?"
SUBTITLE = "A Self-Evolving Harness for Memory-Dependent Manipulation"


def group(text, position):
    while position < len(text) and text[position].isspace():
        position += 1
    if text[position] != "{":
        raise ValueError(f"Expected group: {text[position:position+70]}")
    depth, start = 1, position + 1
    position += 1
    while depth:
        if text[position] == "\\":
            position += 2
            continue
        depth += (text[position] == "{") - (text[position] == "}")
        position += 1
    return text[start:position-1], position


def command(text, name, count, callback):
    pattern = re.compile(r"\\" + name + r"(?![A-Za-z])")
    out, last = [], 0
    for match in pattern.finditer(text):
        if match.start() < last:
            continue
        args, end = [], match.end()
        for _ in range(count):
            value, end = group(text, end)
            args.append(value)
        out.extend((text[last:match.start()], callback(*args)))
        last = end
    out.append(text[last:])
    return "".join(out)


def expand_source():
    text = (SOURCE / "main.tex").read_text(encoding="utf-8")
    body = text.split(r"\begin{document}", 1)[1].split(r"\end{document}", 1)[0]
    body = command(body, "input", 1, lambda path: (SOURCE / (path + ".tex")).read_text(encoding="utf-8"))
    return re.sub(r"(?<!\\)%[^\n]*", "", body)


def export_report():
    text = expand_source()
    original = text
    fragments, labels, headings, images = {}, {}, [], []
    counter = {"figure": 0, "table": 0, "equation": 0}
    section = sub = 0
    appendix = False
    current_label = ""
    env = []

    def fragment(value):
        key = f"ASTRAHTMLTOKEN{len(fragments):05d}END"
        fragments[key] = value
        return "\n\n" + key + "\n\n"

    text = command(text, "caseframe", 3, lambda path, first, second:
                   fragment('<div class="case-frame">') + r"\includegraphics{supplementary/20261023-stopcube/figures/" + path + "-front.png}\n\n" + first + r"\par " + second + fragment('</div>'))
    # Only visual layout is removed; all textual arguments remain.
    for name, count in [("captionsetup", 1), ("setlength", 2), ("vspace", 1), ("hspace", 1), ("role", 1)]:
        text = command(text, name, count, lambda *args: "")
    text = re.sub(r"\\(?:FloatBarrier|clearpage|maketitle|centering|raggedright|hfill|noindent|small|footnotesize|scriptsize|bfseries|ttfamily)(?![A-Za-z])", "", text)
    text = re.sub(r"\\bibliographystyle\{[^}]*\}", "", text)
    text = re.sub(r"\\bibliography\{[^}]*\}", lambda _: fragment('REFERENCESPOSITION'), text)
    text = re.sub(r"\\addlinespace(?:\[[^]]*\])?", "", text)
    text = re.sub(r"\\renewcommand\{\\arraystretch\}\{[^}]*\}", "", text)
    text = command(text, "rowcolor", 1, lambda _: "")
    text = command(text, "textcolor", 2, lambda color, content: content)
    text = command(text, "multicolumn", 3, lambda count, align, content:
                   r"\multicolumn{" + count + "}{" + align.replace("@{}", "") + "}{" + content + "}")
    text = text.replace(r"\pifive", r"$\pi_{0.5}$").replace(r"\citepending", r"\citep")

    token = re.compile(r"\\(begin|end)\{([^}]+)\}|\\(section|subsection|paragraph|captionof|caption|label|includegraphics|appendix)(?![A-Za-z])")
    out, last = [], 0
    for match in token.finditer(text):
        if match.start() < last:
            continue
        out.append(text[last:match.start()])
        end = match.end()
        value = ""
        if match.group(1):
            operation, kind = match.group(1), match.group(2)
            if operation == "begin":
                env.append(kind)
                if kind in {"minipage", "figure", "table"}:
                    optional = re.match(r"\s*\[[^]]*\]", text[end:])
                    if optional:
                        end += optional.end()
                if kind == "minipage":
                    _, end = group(text, end)
                    value = fragment('<div class="mini-panel">')
                elif kind in {"figure", "casefigure", "table"}:
                    value = fragment('<div class="publication-panel ' + ('table-panel' if kind == 'table' else 'figure-panel') + '">')
                elif kind == "abstract":
                    value = fragment('<section class="abstract" id="abstract"><h2>Abstract</h2>')
                elif kind in {"tabular", "tabularx"}:
                    if kind == "tabularx":
                        _, end = group(text, end)
                    columns, end = group(text, end)
                    columns = re.sub(r"@\{[^}]*\}", "", columns)
                    columns = re.sub(r"p\{[^}]*\}", "l", columns).replace("X", "l")
                    value = fragment('<div class="table-scroll" tabindex="0" role="region" aria-label="Scrollable report table">') + r"\begin{tabular}{" + columns + "}\n"
                elif kind == "equation":
                    counter["equation"] += 1
                    current_label = str(counter["equation"])
                    value = fragment('<div class="equation">') + r"\begin{equation}"
                else:
                    value = match.group(0)
            else:
                if env and env[-1] == kind:
                    env.pop()
                if kind in {"figure", "casefigure", "table"}:
                    value = fragment('</div>')
                elif kind == "abstract":
                    value = fragment('</section>')
                elif kind in {"tabular", "tabularx"}:
                    value = "\n" + r"\end{tabular}" + fragment('</div>')
                elif kind == "equation":
                    value = r"\end{equation}" + fragment(f'<span class="equation-number">({counter["equation"]})</span></div>')
                elif kind == "minipage":
                    value = fragment('</div>')
                else:
                    value = match.group(0)
        else:
            name = match.group(3)
            if name == "appendix":
                appendix, section, sub = True, 0, 0
                value = fragment('<div class="appendix-divider" id="appendices">Appendices</div>')
            else:
                if name == "includegraphics":
                    optional = re.match(r"\s*\[[^]]*\]", text[end:])
                    if optional:
                        end += optional.end()
                arg, end = group(text, end)
                if name in {"section", "subsection", "paragraph"}:
                    if name == "section":
                        section, sub = section + 1, 0
                        current_label = chr(64 + section) if appendix else str(section)
                        level = 2
                    elif name == "subsection":
                        sub += 1
                        current_label = (chr(64 + section) if appendix else str(section)) + "." + str(sub)
                        level = 3
                    else:
                        level = 4 if sub else 3
                    following = re.match(r"\s*\\label\{([^}]+)\}", text[end:])
                    identifier = following[1] if following else re.sub(r"[^a-z0-9]+", "-", arg.lower()).strip("-")
                    if following:
                        labels[identifier] = current_label
                        end += following.end()
                    number = current_label if name != "paragraph" else ""
                    headings.append({"id": identifier, "title": arg, "number": number, "level": level})
                    heading_class = ' class="paragraph-heading"' if name == 'paragraph' else ''
                    value = fragment(f'<h{level} id="{identifier}"{heading_class}>' + (f'<span class="section-number">{number}</span> ' if number else '') + html.escape(arg) + f'</h{level}>')
                elif name in {"caption", "captionof"}:
                    kind = arg if name == "captionof" else ("table" if "table" in env else "figure")
                    if name == "captionof":
                        arg, end = group(text, end)
                    counter[kind] += 1
                    current_label = str(counter[kind])
                    value = fragment('<div class="caption">') + r"\textbf{" + kind.title() + " " + current_label + ".} " + arg + fragment('</div>')
                elif name == "label":
                    labels[arg] = current_label
                    value = fragment(f'<span class="reference-anchor" id="{arg}"></span>')
                elif name == "includegraphics":
                    original_image = arg
                    if arg == "teaser.pdf":
                        path = SOURCE / "figures/teaser-drafts/teaser-v3.svg"
                    elif "/" not in arg:
                        path = SOURCE / "figures" / arg.replace(".pdf", ".svg")
                    else:
                        path = SOURCE / arg
                    destination = OUT / "assets/images" / path.name
                    if path.suffix == '.svg':
                        # Keep strokes proportional when a full paper figure shrinks on mobile.
                        destination.write_text(path.read_text(encoding='utf-8').replace('*{vector-effect:non-scaling-stroke}', ''), encoding='utf-8')
                    else:
                        shutil.copyfile(path, destination)
                    images.append(original_image)
                    alt = path.stem.replace("-", " ")
                    value = fragment(f'<a class="zoom-image" href="../assets/images/{path.name}" data-zoom aria-label="Enlarge {html.escape(alt)}"><img src="../assets/images/{path.name}" loading="lazy" alt="{html.escape(alt)}"></a>')
        out.append(value)
        last = end
    out.append(text[last:])
    normalized = "".join(out)
    normalized = command(normalized, "ref", 1, lambda key: r"\href{\#" + key + "}{" + labels[key] + "}")
    normalized = command(normalized, "eqref", 1, lambda key: r"\href{\#" + key + "}{(" + labels[key] + ")}")
    preamble = r"\documentclass{article}\usepackage{amsmath,hyperref,natbib}\begin{document}" + "\n"
    normalized = preamble + normalized + r"\end{document}"
    (CACHE / "normalized.tex").write_text(normalized, encoding="utf-8")
    run = subprocess.run(["pandoc", "--from=latex", "--to=html5", "--citeproc", "--mathml",
                          "--bibliography=" + str(SOURCE / "references.bib"),
                          "--csl=" + str(ROOT / "templates/numeric.csl"), "--metadata=link-citations:true"],
                         input=normalized, encoding="utf-8", capture_output=True, check=True)
    if run.stderr.strip():
        print(run.stderr)
    rendered = run.stdout
    for key, value in fragments.items():
        if key not in rendered:
            raise ValueError("Dropped HTML marker: " + key)
        rendered = rendered.replace("<p>" + key + "</p>", value)
        rendered = rendered.replace(key, value)
    # Keep bibliography at the paper's original position, before the appendices.
    refs = rendered.find('<div id="refs"')
    if refs >= 0:
        bibliography = rendered[refs:]
        rendered = rendered[:refs].replace('REFERENCESPOSITION', '<h2 id="references">References</h2>' + bibliography)
    else:
        raise ValueError("Missing bibliography")
    rendered = re.sub(r'<p>\s*</p>', '', rendered)
    # Paragraph-sized groups created by minipage styling may surround block markers.
    rendered = re.sub(r'<p>\s*(<(?:div|section|h[234]|a class="zoom-image")[^>]*>)', r'\1', rendered)
    rendered = re.sub(r'(</(?:div|section|h[234])>)\s*</p>', r'\1', rendered)
    (CACHE / "report-body.html").write_text(rendered, encoding="utf-8")
    outline = [{"id": "abstract", "title": "Abstract", "number": "", "level": 2}] + headings
    toc = ''
    for item in outline:
        if item['number'] == 'A':
            toc += '<a href="#references">References</a>'
        if item['level'] < 4 and (item['number'] or item['id'] == 'abstract'):
            toc += f'<a class="toc-level-{item["level"]}" href="#{item["id"]}">{item["number"]} {html.escape(item["title"])}</a>'
    template = (ROOT / "templates/report.html").read_text(encoding="utf-8")
    page = template.replace("{{TITLE}}", TITLE).replace("{{SUBTITLE}}", SUBTITLE).replace("{{TOC}}", toc).replace("{{BODY}}", rendered)
    (OUT / "report").mkdir(exist_ok=True)
    page = '\n'.join(line.rstrip() for line in page.splitlines()) + '\n'
    (OUT / "report/index.html").write_text(page, encoding="utf-8")
    expected_headings = len(re.findall(r"\\(?:section|subsection|paragraph)\{", original))
    if expected_headings != len(headings):
        raise ValueError(f"Lost headings: {expected_headings} != {len(headings)}")
    inventory = {"headings": headings, "figures": counter["figure"], "tables": counter["table"],
                 "equations": counter["equation"], "images": images, "labels": labels}
    (ROOT / "content/report-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return inventory


def build_home():
    data = json.loads((SOURCE / "figures/task_comparison_data.json").read_text(encoding="utf-8"))
    data["sources"]["Our harness"] = "report/#app:task-results"
    (OUT / "assets/results.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    videos = json.loads((ROOT / "content/videos.json").read_text(encoding="utf-8-sig"))
    (OUT / "assets/videos.json").write_text(json.dumps(videos, indent=2) + "\n", encoding="utf-8")
    suites = ["Counting", "Permanence", "Reference", "Imitation"]
    rows = []
    for index, task in enumerate(data["tasks"]):
        values = [data["series"][key][index] for key in ["Our harness", "Astra (direct)", "Human", "GroundSG+Oracle"]]
        rows.append(f'<tr data-suite="{suites[index//4]}"><th scope="row">{task}</th><td>{suites[index//4]}</td>' + ''.join(f'<td>{value:g}%</td>' for value in values) + '</tr>')
    cards = ''.join(f'<a class="task-tab" href="assets/videos/{item["slug"]}.mp4" data-video="{index}"><span>{item["suite"]}</span><strong>{item["task"]}</strong></a>' for index, item in enumerate(videos))
    template = (ROOT / "templates/home.html").read_text(encoding="utf-8")
    successes = sum(value * .5 for value in data['series']['Our harness'])
    episodes = len(data['tasks']) * 50
    experiments = (SOURCE / 'sections/experiments.tex').read_text(encoding='utf-8')
    allocations = {}
    for label in ['Subgoal entry', 'Astra intervention', 'Automatic VLA continuation', 'VLA continuation after review']:
        allocations[label] = float(re.search(re.escape(label) + r'\s*&\s*([\d.]+)', experiments)[1])
    auto_rate = allocations['Automatic VLA continuation']
    replacements = {
        '{{SUCCESS_RATE}}': f'{successes / episodes * 100:.1f}',
        '{{SUCCESSES}}': str(int(successes)), '{{EPISODES}}': str(episodes),
        '{{AUTO_ROUNDED}}': f'{auto_rate:.1f}', '{{AUTO_EXACT}}': f'{auto_rate:.2f}',
        '{{ENTRY_RATE}}': f'{allocations["Subgoal entry"]:.2f}',
        '{{INTERVENTION_RATE}}': f'{allocations["Astra intervention"]:.2f}',
        '{{REVIEWED_RATE}}': f'{allocations["VLA continuation after review"]:.2f}',
    }
    for index, suite in enumerate(suites):
        replacements['{{' + suite.upper() + '_RATE}}'] = f'{sum(data["series"]["Our harness"][index*4:index*4+4])/4:.1f}'
    for key, value in replacements.items():
        template = template.replace(key, value)
    teaser = (SOURCE / "figures/teaser-drafts/teaser-v3.svg").read_text(encoding="utf-8")
    scene_defs = re.search(r"<defs>.*?</defs>", teaser, re.S).group(0)
    page = template.replace("{{TASK_ROWS}}", ''.join(rows)).replace("{{VIDEO_TABS}}", cards).replace("{{SCENE_DEFS}}", scene_defs)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    for name in ["sysu-logo.svg", "tengenx-logo.png"]:
        shutil.copyfile(SOURCE / "figures" / name, OUT / "assets/images" / name)
    for name in ["site.css", "site.js", "favicon.svg"]:
        shutil.copyfile(ROOT / "templates" / name, OUT / "assets" / name)
    (OUT / ".nojekyll").touch()


def build_pdf():
    temporary = CACHE / "pdf-source"
    shutil.copytree(SOURCE, temporary, dirs_exist_ok=True)
    run = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                         cwd=temporary, capture_output=True)
    (CACHE / "latex-build.log").write_bytes(run.stdout + run.stderr)
    if run.returncode:
        raise RuntimeError("PDF build failed; see .cache/latex-build.log")
    shutil.copyfile(temporary / "main.pdf", OUT / "assets/technical-report.pdf")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    for directory in [CACHE, OUT / "assets/images", OUT / "report"]:
        directory.mkdir(parents=True, exist_ok=True)
    inventory = export_report()
    build_home()
    if args.pdf:
        build_pdf()
    print(f'Built {len(inventory["headings"])} headings, {inventory["figures"]} figures, {inventory["tables"]} tables, {inventory["equations"]} equations.')
