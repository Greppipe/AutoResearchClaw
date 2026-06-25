#!/usr/bin/env python3
"""
SCI Research Platform — Interactive CLI Launcher
=================================================
Double-click launch.bat  OR  python run.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import subprocess
from pathlib import Path

ROOT    = Path(__file__).parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
for _f in (ROOT / ".env.local", ROOT / ".env"):
    if _f.exists():
        load_dotenv(_f, override=True)
        break

_provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
_key_map  = {
    "anthropic": "ANTHROPIC_API_KEY",
    "groq":      "GROQ_API_KEY",
    "gemini":    "GEMINI_API_KEY",
    "ollama":    None,
}
_required_key = _key_map.get(_provider)
if _required_key and not os.environ.get(_required_key):
    print(f"\n[ERROR] {_required_key} not set for provider '{_provider}'.")
    print(f"  Edit {ROOT / '.env.local'} and add your key.")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    from rich.align import Align
    from rich import box
    import questionary
    from questionary import Style as QStyle
except ImportError:
    print("[ERROR] pip install rich questionary")
    sys.exit(1)

console = Console()

Q = QStyle([
    ("qmark",       "fg:#1a73e8 bold"),
    ("question",    "bold"),
    ("answer",      "fg:#2da44e bold"),
    ("pointer",     "fg:#1a73e8 bold"),
    ("highlighted", "fg:#1a73e8 bold"),
    ("selected",    "fg:#2da44e"),
    ("instruction", "fg:#888888"),
])

DOMAINS = [
    "Artificial Intelligence & Machine Learning",
    "Biomedical Engineering",
    "Clinical Medicine & Public Health",
    "Computer Science & Software Engineering",
    "Chemistry & Materials Science",
    "Civil & Structural Engineering",
    "Data Science & Analytics",
    "Economics & Finance",
    "Electrical & Electronic Engineering",
    "Environmental Science",
    "Food Science & Nutrition",
    "Genetics & Molecular Biology",
    "Mechanical Engineering",
    "Neuroscience & Cognitive Science",
    "Pharmacy & Drug Discovery",
    "Physics & Astronomy",
    "Psychology & Behavioral Science",
    "Renewable Energy & Sustainability",
    "Robotics & Automation",
    "Social Sciences & Education",
    "Other",
]
STUDY_TYPES = [
    "Experimental Study",
    "Clinical Trial / RCT",
    "Systematic Review / Meta-analysis",
    "Observational / Cohort Study",
    "Survey / Cross-sectional Study",
    "Computational / Simulation Study",
    "Case Study",
    "Theoretical / Conceptual Paper",
]
CITATION_STYLES = ["IEEE", "APA", "Harvard", "Vancouver", "Chicago", "MLA"]
JOURNAL_TYPES   = ["SCI", "SCI-E", "SCIE", "ESCI", "Scopus", "Q1", "Q2"]
TONES           = ["Academic", "Technical", "Formal", "Analytical", "Interdisciplinary"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _banner():
    console.print(Panel.fit(
        "[bold #1a73e8]SCI Research Platform[/]  [dim]v2.0 — Local CLI[/]\n"
        "[dim]Claude Opus 4.7 · Deep Document Intelligence · LangGraph[/]",
        border_style="#1a1a2e", padding=(1, 4),
    ))
    console.print()


def _section(title: str):
    console.print(f"\n[bold #1a1a2e]── {title} ──[/]")


def _ask(q: str, default: str = "", validate=None) -> str:
    kw = {"style": Q}
    if validate:
        kw["validate"] = validate
    return questionary.text(q, default=default, **kw).ask() or default


def _select(q: str, choices: list, default=None) -> str:
    return questionary.select(q, choices=choices,
                               default=default or choices[0], style=Q).ask()


def _confirm(q: str, default: bool = True) -> bool:
    return questionary.confirm(q, default=default, style=Q).ask()


def _ask_files() -> list[str]:
    paths: list[str] = []
    console.print("\n[dim]  Drag-and-drop files into terminal, or type full paths. Press Enter with blank to finish.[/]")
    while True:
        raw = questionary.path(
            f"  File {len(paths)+1} (Enter to finish):", style=Q
        ).ask()
        if not raw or not raw.strip():
            break
        p = Path(raw.strip().strip('"'))
        if p.exists():
            paths.append(str(p))
            console.print(f"  [green]✓[/] {p.name}  [dim]{p.stat().st_size // 1024} KB[/]")
        else:
            console.print(f"  [red]✗ Not found:[/] {p}")
    return paths


def _collect_authors(lead_name: str, lead_aff: str) -> list[dict]:
    authors = [{"name": lead_name, "affiliation": lead_aff, "email": ""}]
    while True:
        name = _ask(f"  Co-author {len(authors)} name (Enter to finish):").strip()
        if not name:
            break
        aff   = _ask(f"  {name}'s affiliation:").strip()
        email = _ask(f"  {name}'s email (optional):").strip()
        authors.append({"name": name, "affiliation": aff, "email": email})
    return authors


# ── Wizard ────────────────────────────────────────────────────────────────────

def _collect_params() -> dict:

    _section("STEP 1 — Research Identity")
    title      = _ask("Paper title:", validate=lambda v: True if v.strip() else "Required")
    domain     = _select("Research domain:", DOMAINS)
    study_type = _select("Study type:", STUDY_TYPES)
    kw_raw     = _ask("Keywords (comma-separated, 6–8 recommended):")
    keywords   = [k.strip() for k in kw_raw.split(",") if k.strip()]

    _section("STEP 2 — Research Problem")
    console.print("[dim]  Tip: be specific — include numbers, populations, challenges[/]")
    problem_statement  = _ask("What problem does this research address?")
    research_gap       = _ask("What gap in existing literature does this fill?")
    hypothesis         = _ask("State your hypothesis or central research question:")
    novel_contribution = _ask("What is the single most novel contribution?")
    research_significance = _ask("Why does this matter? (societal / clinical / tech impact):")

    _section("STEP 3 — Authors & Ethics")
    author_name        = _ask("Lead author full name:")
    author_affiliation = _ask("Lead author institution:")
    all_authors = [{"name": author_name, "affiliation": author_affiliation, "email": ""}]
    if _confirm("Add co-authors?", default=False):
        all_authors = _collect_authors(author_name, author_affiliation)
    funding_source = _ask("Funding source / grant number (blank = none):")
    coi            = _ask("Conflicts of interest (blank = none declared):")
    ethics         = _ask("Ethics statement / IRB approval (blank if N/A):")

    _section("STEP 4 — Methodology & Data")
    console.print("[dim]  Tip: include study design, sample size, and key procedures[/]")
    methodology_description = _ask("Describe your methodology:")
    dataset_description     = _ask("Dataset / study subjects (size, source, criteria):")
    analysis_methods        = _ask("Statistical / computational methods (tools, versions):")
    tools_used              = _ask("Software, hardware, or APIs used:")
    expected_findings       = _ask("Key expected or actual findings (include numbers):")
    objectives              = _ask("Research objectives (brief):")

    _section("STEP 5 — Output Settings")
    journal_type   = _select("Target journal tier:", JOURNAL_TYPES)
    citation_style = _select("Citation style:", CITATION_STYLES).lower()
    wc_str         = _ask("Target word count:", default="8000")
    try:
        word_count = int(wc_str.replace(",", "").strip())
    except ValueError:
        word_count = 8000
    writing_tone = _select("Writing tone:", TONES).lower()
    additional   = _ask("Additional instructions (optional):")

    return dict(
        title=title, domain=domain, keywords=keywords, study_type=study_type,
        problem_statement=problem_statement, research_gap=research_gap,
        hypothesis=hypothesis, novel_contribution=novel_contribution,
        research_significance=research_significance, objectives=objectives,
        author_name=author_name, author_affiliation=author_affiliation,
        all_authors=all_authors, funding_source=funding_source,
        conflicts_of_interest=coi, ethics_statement=ethics,
        methodology_description=methodology_description,
        dataset_description=dataset_description,
        analysis_methods=analysis_methods, tools_used=tools_used,
        expected_findings=expected_findings,
        journal_type=journal_type, citation_style=citation_style,
        preferred_word_count=word_count, writing_tone=writing_tone,
        additional_instructions=additional,
    )


# ── Cost estimate panel ──────────────────────────────────────────────────────

def _show_cost_estimate(params: dict, file_count: int, mode: str):
    from app.local_pipeline import estimate_cost
    est = estimate_cost(params, file_count)
    if mode == "summary":
        est["estimated_usd"] = round(est["estimated_usd"] * 0.12, 2)
        est["low_usd"]       = round(est["low_usd"]       * 0.12, 2)
        est["high_usd"]      = round(est["high_usd"]      * 0.12, 2)

    console.print(Panel(
        f"[dim]Estimated API cost:[/]  "
        f"[bold]${est['low_usd']:.2f} – ${est['high_usd']:.2f}[/]  "
        f"[dim](≈ ${est['estimated_usd']:.2f} typical)[/]\n"
        f"[dim]Tokens:[/]  ~{est['input_tokens']:,} in · ~{est['output_tokens']:,} out  "
        f"[dim](Claude Opus 4.7 + Sonnet 4.6)[/]",
        title="[dim]Cost Estimate[/]",
        border_style="dim",
        padding=(0, 2),
    ))
    console.print()


# ── Config summary table ──────────────────────────────────────────────────────

def _show_summary(params: dict, file_paths: list, mode: str):
    t = Table(title="Run Configuration", box=box.ROUNDED,
              show_header=True, header_style="bold #1a1a2e")
    t.add_column("Field", style="dim", width=26)
    t.add_column("Value", style="bold")
    for k, v in [
        ("Mode",        f"[cyan]{mode}[/]"),
        ("Title",       params["title"][:60]),
        ("Domain",      params["domain"]),
        ("Study Type",  params["study_type"]),
        ("Lead Author", f"{params['author_name']} · {params['author_affiliation']}"),
        ("Co-authors",  str(len(params["all_authors"]) - 1)),
        ("Journal",     params["journal_type"]),
        ("Citation",    params["citation_style"].upper()),
        ("Word Count",  f"~{params['preferred_word_count']:,}"),
        ("Files",       str(len(file_paths))),
        ("Keywords",    ", ".join(params["keywords"][:5])),
    ]:
        t.add_row(k, v)
    console.print()
    console.print(t)
    console.print()


# ── Live two-pane progress display ────────────────────────────────────────────

async def _run_with_live_display(coro, mode_label: str) -> dict:
    """
    Run pipeline coroutine while showing:
      - Top pane:    spinner + step description + % bar
      - Bottom pane: live preview of generated paper content
    """
    result_box: list = []
    error_box:  list = []

    # Shared state updated by callback
    live_state = {"msg": f"Starting {mode_label}...", "pct": 0.0, "preview": ""}

    layout = Layout()
    layout.split_column(
        Layout(name="progress", size=6),
        Layout(name="preview"),
    )

    def _render():
        pct  = live_state["pct"]
        msg  = live_state["msg"]
        prev = live_state["preview"]

        bar_width = 44
        filled    = int(bar_width * pct / 100)
        bar       = "█" * filled + "░" * (bar_width - filled)

        progress_text = (
            f"  [bold]{msg}[/]\n"
            f"  [#1a73e8]{bar}[/]  [bold]{pct:.0f}%[/]"
        )
        layout["progress"].update(Panel(
            progress_text,
            title=f"[bold #1a73e8]{mode_label}[/]",
            border_style="#1a1a2e",
            padding=(0, 1),
        ))

        if prev:
            layout["preview"].update(Panel(
                Text(prev[:800], overflow="fold"),
                title="[dim]Live Preview — Paper Content[/]",
                border_style="dim",
                padding=(0, 1),
            ))
        else:
            layout["preview"].update(Panel(
                "[dim]Content will appear here as each section is written...[/]",
                title="[dim]Live Preview[/]",
                border_style="dim",
                padding=(0, 1),
            ))
        return layout

    def _cb(message: str, pct: float, content: str = ""):
        live_state["msg"]     = message
        live_state["pct"]     = pct
        live_state["preview"] = content or live_state["preview"]

    async def _runner():
        try:
            result_box.append(await coro(_cb))
        except Exception as e:
            error_box.append(e)

    with Live(_render(), refresh_per_second=6, console=console) as live:
        runner_task = asyncio.create_task(_runner())
        while not runner_task.done():
            live.update(_render())
            await asyncio.sleep(0.18)
        live.update(_render())

    if error_box:
        raise error_box[0]
    return result_box[0] if result_box else {}


# ── Resume detection ──────────────────────────────────────────────────────────

def _offer_resume() -> Optional[str]:
    """Check for incomplete runs and offer to resume. Returns project_id or None."""
    try:
        from app.local_pipeline import scan_incomplete_runs
        runs = scan_incomplete_runs()
        if not runs:
            return None
        console.print(Panel(
            "\n".join(
                f"  [cyan]{r['project_id']}[/]  {r['title'][:50]}  "
                f"[dim](stopped at: {r['last_step']})[/]"
                for r in runs[:5]
            ),
            title="[bold yellow]Incomplete runs found[/]",
            border_style="yellow",
        ))
        console.print()
        if _confirm(f"Resume the most recent incomplete run?", default=True):
            return runs[0]["project_id"]
    except Exception:
        pass
    return None


def _open_folder(path: str):
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception:
        pass


# ── Async pipeline runner (no questionary calls inside) ──────────────────────

async def _run_pipeline(params: dict, file_paths: list, mode: str,
                        resume_pid, mode_label: str) -> dict:
    from app.local_pipeline import run_paper, run_summary

    if mode == "paper":
        async def _coro(cb):
            return await run_paper(params, file_paths,
                                   progress_callback=cb,
                                   resume_project_id=resume_pid)
    else:
        async def _coro(cb):
            return await run_summary(params, file_paths, progress_callback=cb)

    return await _run_with_live_display(_coro, mode_label)


# ── Main — sync wizard first, then async pipeline ────────────────────────────

def main():
    try:
        _banner()

        # License check (sync)
        try:
            from app.license import check_license_file
            ok, msg = check_license_file()
            if not ok and msg != "no_license":
                console.print(f"[bold red]License error:[/] {msg}")
                sys.exit(1)
        except Exception:
            pass

        # Resume check (sync)
        resume_pid = _offer_resume()

        if resume_pid:
            params     = {}
            file_paths = []
            mode       = "paper"
            mode_label = "Full SCI Paper (Resume)"
        else:
            draft_file = ROOT / ".draft_run.json"
            draft = {}
            if draft_file.exists():
                try:
                    import json
                    with open(draft_file, "r", encoding="utf-8") as f:
                        draft = json.load(f)
                except Exception:
                    pass

            use_draft = False
            if draft and _confirm("Found saved data from your previous session. Reload it? (No = start fresh with new topic)", default=False):
                use_draft = True
                params = draft.get("params", {})
                file_paths = draft.get("file_paths", [])
                mode = draft.get("mode", "paper")
            
            if not use_draft:
                # ── All questionary prompts run here — sync, no event loop ──
                params = _collect_params()

                _section("STEP 6 — Upload Reference Files")
                console.print("[dim]  These files ground the AI in YOUR data (optional but recommended)[/]")
                file_paths = _ask_files()

                console.print()
                mode = questionary.select(
                    "What would you like to generate?",
                    choices=[
                        questionary.Choice(
                            "1. Full SCI Paper  (Top-1% quality · Word + LaTeX · ~15–35 min)",
                            value="paper"),
                        questionary.Choice(
                            "2. Research Summary  (Structured report · ~3–8 min)",
                            value="summary"),
                    ],
                    style=Q,
                ).ask()

                if not mode:
                    console.print("[yellow]Cancelled.[/]")
                    sys.exit(0)

                # Save draft so user doesn't lose it if a crash occurs right after
                try:
                    import json
                    with open(draft_file, "w", encoding="utf-8") as f:
                        json.dump({"params": params, "file_paths": file_paths, "mode": mode}, f, indent=2)
                except Exception:
                    pass

            mode_label = "Full SCI Paper" if mode == "paper" else "Research Summary"
            _show_summary(params, file_paths, mode_label)
            _show_cost_estimate(params, len(file_paths), mode)

        console.print(f"[bold #1a73e8]Launching {mode_label} pipeline...[/]\n")

        # ── Async pipeline — started fresh here, no nested event loop ──
        result = asyncio.run(
            _run_pipeline(params, file_paths, mode, resume_pid, mode_label)
        )

        # Results panel
        console.print()
        if mode == "paper":
            console.print(Panel(
                f"[bold green]✓  SCI Paper Generated![/]\n\n"
                f"  [dim]Editor Score[/]     [bold]{result.get('editor_score',0):.1f}[/] / 10\n"
                f"  [dim]Plagiarism[/]       [bold]{result.get('plagiarism_score',0):.1f}%[/]\n"
                f"  [dim]AI Detection[/]     [bold]{result.get('ai_detection_score',0):.1f}%[/]\n"
                f"  [dim]References[/]       [bold]{result.get('reference_count',0)}[/] verified\n"
                f"  [dim]Charts[/]           [bold]{result.get('chart_count',0)}[/] embedded\n"
                f"  [dim]Tables[/]           [bold]{result.get('table_count',0)}[/] rendered\n\n"
                f"  [dim]Output folder[/]    [bold cyan]{result.get('output_dir','')}[/]",
                title="[bold #1a73e8]Pipeline Complete[/]",
                border_style="#2da44e", padding=(1, 2),
            ))
        else:
            console.print(Panel(
                f"[bold green]✓  Research Summary Generated![/]\n\n"
                f"  [italic]{(result.get('one_sentence_summary',''))[:120]}[/]\n\n"
                f"  [dim]Output folder[/]    [bold cyan]{result.get('output_dir','')}[/]",
                title="[bold #1a73e8]Summary Complete[/]",
                border_style="#2da44e", padding=(1, 2),
            ))

        out_dir = result.get("output_dir", "")
        if out_dir and Path(out_dir).exists():
            ft = Table(title="Output Files", box=box.SIMPLE,
                       show_header=True, header_style="bold")
            ft.add_column("File", style="cyan")
            ft.add_column("Size", justify="right", style="dim")
            for f in sorted(Path(out_dir).glob("*")):
                ft.add_row(f.name, f"{f.stat().st_size // 1024} KB")
            console.print(ft)

        if out_dir:
            _open_folder(out_dir)

        console.print("\n[bold #1a73e8]Thank you for using SCI Research Platform.[/]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
