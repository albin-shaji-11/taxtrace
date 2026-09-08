"""Render the project's Markdown documentation to PDF.

No pandoc, no cloud service, no paid tooling. This converts the Markdown
subset actually used in docs/ into LaTeX and compiles it with the local
MiKTeX installation.

    python scripts/md_to_pdf.py                 # every doc, plus a combined pack
    python scripts/md_to_pdf.py docs/day01.md   # one file

Output goes to docs/pdf/.

Supported Markdown: ATX headings, paragraphs, bold, italic, inline code,
fenced code blocks, pipe tables, bullet and numbered lists, task list
checkboxes, blockquotes, horizontal rules, links, and <details>/<summary>
blocks (rendered as labelled hint boxes).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "pdf"

PDFLATEX = r"C:\Users\Albin Shaji\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"

# Documents in reading order, with the titles that go on each cover line.
DOCS: list[tuple[str, str]] = [
    ("README.md", "TaxTrace, project overview"),
    ("docs/skill_matrix.md", "Skill matrix, Deloitte Tax Data Automation"),
    ("docs/business_requirements.md", "Business requirements, Meridian Commerce Group"),
    ("docs/architecture.md", "Architecture"),
    ("docs/study_plan.md", "Seven day study plan"),
    ("docs/day01.md", "Day 1, messy data and profiling"),
]

UNICODE_MAP = {
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "\u2014": "--", "\u2013": "-", "\u2026": "...", "\u00a0": " ",
    "\u2192": "->", "\u2190": "<-", "\u00d7": "x", "\u00b1": "+/-",
    "\u00a3": "GBP ", "\u20ac": "EUR ", "\u2713": "[x]", "\u2717": "[ ]",
}

PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{charter}
\usepackage[margin=2.2cm,top=2.4cm,bottom=2.4cm]{geometry}
\usepackage{longtable}
\usepackage{array}
\usepackage{booktabs}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\usepackage{needspace}
\usepackage{framed}
\usepackage{amssymb}

\definecolor{codebg}{RGB}{246,246,244}
\definecolor{rulegrey}{RGB}{120,120,120}
\definecolor{linkblue}{RGB}{20,70,140}

\lstset{
  basicstyle=\ttfamily\footnotesize,
  backgroundcolor=\color{codebg},
  frame=single,
  rulecolor=\color{rulegrey},
  framesep=5pt,
  breaklines=true,
  breakatwhitespace=false,
  columns=fullflexible,
  keepspaces=true,
  showstringspaces=false,
  xleftmargin=2pt,
  aboveskip=8pt,
  belowskip=8pt,
  literate={->}{{$\rightarrow$}}2 {|}{{\textbar}}1
}

\titleformat{\section}{\Large\bfseries}{}{0em}{}[\vspace{-6pt}\rule{\linewidth}{0.6pt}]
\titleformat{\subsection}{\large\bfseries}{}{0em}{}
\titleformat{\subsubsection}{\normalsize\bfseries}{}{0em}{}
\titlespacing{\section}{0pt}{16pt}{6pt}
\titlespacing{\subsection}{0pt}{12pt}{4pt}
\titlespacing{\subsubsection}{0pt}{10pt}{3pt}

\setlist[itemize]{leftmargin=1.4em,topsep=3pt,itemsep=1pt,parsep=0pt}
\setlist[enumerate]{leftmargin=1.6em,topsep=3pt,itemsep=1pt,parsep=0pt}

\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\raggedright
\tolerance=9999
\emergencystretch=3em

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0.4pt}
\fancyhead[L]{\small\textsc{TaxTrace}}
\fancyhead[R]{\small DOCTITLE}
\fancyfoot[C]{\small\thepage}
"""


def sanitise(text: str) -> str:
    for bad, good in UNICODE_MAP.items():
        text = text.replace(bad, good)
    return text


def esc(text: str) -> str:
    """Escape LaTeX special characters in plain prose."""
    out = text.replace("\\", r"\textbackslash{}")
    for ch in "&%$#_{}":
        out = out.replace(ch, "\\" + ch)
    out = out.replace("~", r"\textasciitilde{}").replace("^", r"\textasciicircum{}")
    return out


def inline(text: str) -> str:
    """Convert inline Markdown to LaTeX, protecting code spans first."""
    spans: list[str] = []

    def stash(m: re.Match) -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = esc(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)          # links, keep the label
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\\emph{\1}", text)

    def restore(m: re.Match) -> str:
        return r"\texttt{\small " + esc(spans[int(m.group(1))]) + "}"

    return re.sub(r"\x00(\d+)\x00", restore, text)


def table(rows: list[str]) -> str:
    """Convert a pipe table into a longtable that can break across pages."""
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    header = cells(rows[0])
    body = [cells(r) for r in rows[2:] if r.strip()]
    n = len(header)
    # First column narrower, the rest share what is left.
    spec = "@{}p{0.22\\linewidth}" + "".join(
        [f"p{{{0.74 / max(1, n - 1):.3f}\\linewidth}}" for _ in range(n - 1)]) + "@{}"
    if n == 1:
        spec = "@{}p{\\linewidth}@{}"

    out = [r"{\small\begin{longtable}{" + spec + "}", r"\toprule"]
    out.append(" & ".join(r"\textbf{%s}" % inline(h) for h in header) + r" \\")
    out.append(r"\midrule\endhead")
    for row in body:
        row = (row + [""] * n)[:n]
        out.append(" & ".join(inline(c) for c in row) + r" \\")
    out += [r"\bottomrule", r"\end{longtable}}"]
    return "\n".join(out)


def convert(md: str) -> str:
    md = sanitise(md)
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    list_stack: list[str] = []

    def close_lists() -> None:
        while list_stack:
            out.append(r"\end{%s}" % list_stack.pop())

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # fenced code block
        if line.strip().startswith("```"):
            close_lists()
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            out.append(r"\begin{lstlisting}")
            out.extend(block)
            out.append(r"\end{lstlisting}")
            continue

        # details / summary hint boxes
        if line.strip().startswith("<details>"):
            close_lists()
            i += 1
            continue
        if line.strip().startswith("</details>"):
            i += 1
            continue
        m = re.match(r"\s*<summary>(.*?)</summary>", line)
        if m:
            out.append(r"\needspace{3\baselineskip}")
            out.append(r"\textbf{" + inline(m.group(1)) + r"}\\[-2pt]")
            i += 1
            continue

        # table
        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$",
                                                           lines[i + 1]):
            close_lists()
            block = []
            while i < len(lines) and "|" in lines[i]:
                block.append(lines[i])
                i += 1
            out.append(table(block))
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_lists()
            depth = len(m.group(1))
            cmd = {1: "section", 2: "section", 3: "subsection"}.get(depth, "subsubsection")
            out.append("\\%s*{%s}" % (cmd, inline(m.group(2))))
            i += 1
            continue

        # horizontal rule
        if re.match(r"^\s*(---|\*\*\*|___)\s*$", line):
            close_lists()
            out.append(r"\vspace{2pt}\rule{\linewidth}{0.4pt}\vspace{2pt}")
            i += 1
            continue

        # blockquote
        if line.strip().startswith(">"):
            close_lists()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(r"\begin{leftbar}\emph{" + inline(" ".join(quote)) + r"}\end{leftbar}")
            continue

        # task list
        m = re.match(r"^(\s*)- \[( |x|X)\]\s+(.*)$", line)
        if m:
            if not list_stack or list_stack[-1] != "itemize":
                close_lists()
                out.append(r"\begin{itemize}[label={}]")
                list_stack.append("itemize")
            box = r"$\boxtimes$" if m.group(2).lower() == "x" else r"$\square$"
            out.append(r"\item " + box + " " + inline(m.group(3)))
            i += 1
            continue

        # bullets
        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m:
            if not list_stack or list_stack[-1] != "itemize":
                close_lists()
                out.append(r"\begin{itemize}")
                list_stack.append("itemize")
            out.append(r"\item " + inline(m.group(2)))
            i += 1
            continue

        # numbered
        m = re.match(r"^(\s*)\d+[.)]\s+(.*)$", line)
        if m:
            if not list_stack or list_stack[-1] != "enumerate":
                close_lists()
                out.append(r"\begin{enumerate}")
                list_stack.append("enumerate")
            out.append(r"\item " + inline(m.group(2)))
            i += 1
            continue

        # blank line
        if not line.strip():
            close_lists()
            out.append("")
            i += 1
            continue

        close_lists()
        out.append(inline(line.strip()))
        i += 1

    close_lists()
    return "\n".join(out)


def build_pdf(md_path: Path, title: str, out_dir: Path) -> Path | None:
    body = convert(md_path.read_text(encoding="utf-8"))
    stem = md_path.stem
    tex = (PREAMBLE.replace("DOCTITLE", esc(title))
           + "\n\\begin{document}\n" + body + "\n\\end{document}\n")
    tex_path = out_dir / f"{stem}.tex"
    tex_path.write_text(tex, encoding="utf-8")

    for _ in range(2):  # twice so longtable column widths settle
        subprocess.run([PDFLATEX, "-interaction=nonstopmode",
                        f"-output-directory={out_dir}", str(tex_path)],
                       capture_output=True)
    for ext in (".aux", ".log", ".out", ".tex"):
        p = out_dir / (stem + ext)
        if p.exists():
            p.unlink()
    pdf = out_dir / f"{stem}.pdf"
    return pdf if pdf.exists() else None


def build_pack(out_dir: Path) -> Path | None:
    """One combined PDF of every doc, in reading order, with a contents page."""
    parts = [
        r"\begin{titlepage}\vspace*{5cm}\centering",
        r"{\Huge\textbf{TaxTrace}}\\[10pt]",
        r"{\Large Reading pack}\\[18pt]",
        r"{\large Deloitte, Analyst Tax Data Automation}\\[4pt]",
        r"{\large Seven day preparation}\\[30pt]",
        r"\end{titlepage}",
        r"\tableofcontents\newpage",
    ]
    for rel, title in DOCS:
        src = ROOT / rel
        if not src.exists():
            continue
        parts.append(r"\phantomsection\addcontentsline{toc}{section}{%s}" % esc(title))
        parts.append(convert(src.read_text(encoding="utf-8")))
        parts.append(r"\clearpage")

    tex = (PREAMBLE.replace("DOCTITLE", "Reading pack")
           + "\n" + r"\begin{document}" + "\n"
           + "\n".join(parts) + "\n" + r"\end{document}" + "\n")
    tex_path = out_dir / "taxtrace_reading_pack.tex"
    tex_path.write_text(tex, encoding="utf-8")
    for _ in range(3):  # three passes so the table of contents resolves
        subprocess.run([PDFLATEX, "-interaction=nonstopmode",
                        f"-output-directory={out_dir}", str(tex_path)],
                       capture_output=True)
    for ext in (".aux", ".log", ".out", ".toc", ".tex"):
        f = out_dir / ("taxtrace_reading_pack" + ext)
        if f.exists():
            f.unlink()
    pdf = out_dir / "taxtrace_reading_pack.pdf"
    return pdf if pdf.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="Markdown files. Default: all project docs.")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    targets = ([(f, Path(f).stem) for f in a.files] if a.files else DOCS)
    made = []
    for rel, title in targets:
        src = ROOT / rel
        if not src.exists():
            print("skip, not found:", rel)
            continue
        pdf = build_pdf(src, title, OUT)
        if pdf:
            made.append(pdf)
            print(f"{pdf.name:<32} {pdf.stat().st_size / 1024:6.1f} KB")
        else:
            print("FAILED:", rel)
    if not a.files:
        pk = build_pack(OUT)
        if pk:
            made.append(pk)
            print(f"{pk.name:<32} {pk.stat().st_size / 1024:6.1f} KB   <- combined")
    print(f"\n{len(made)} PDF(s) in {OUT}")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
