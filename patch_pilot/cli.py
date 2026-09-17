"""
Interactive Command Line Interface for PatchPilot.
Built with Rich and Click for a premier terminal experience.
"""

import os
import sys
import difflib
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown

from patch_pilot import __version__
from patch_pilot.config import Config
from patch_pilot.ast_engine.inspector import CodeInspector
from patch_pilot.llm.provider import LLMProvider
from patch_pilot.agents.supervisor import SupervisorOrchestrator
from patch_pilot.reporter.markdown_builder import MarkdownReportBuilder

# Ensure UTF-8 output encoding across Windows shells
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

BANNER = r"""
[bold cyan] ____       _       _     ____  _ _       _   [/bold cyan]
[bold cyan]|  _ \ __ _| |_ ___| |__ |  _ \(_) | ___ | |_ [/bold cyan]
[bold cyan]| |_) / _` | __/ __| '_ \| |_) | | |/ _ \| __|[/bold cyan]
[bold cyan]|  __/ (_| | || (__| | | |  __/| | | (_) | |_ [/bold cyan]
[bold cyan]|_|   \__,_|\__\___|_| |_|_|   |_|_|\___/ \__|[/bold cyan]
[dim]Autonomous Multi-Agent Code Intelligence & Self-Healing Engine[/dim]
"""


@click.group()
@click.version_option(version=__version__, prog_name="PatchPilot")
def main():
    """PatchPilot: Multi-agent code review, vulnerability detection, and self-healing test synthesizer."""
    pass


@main.command()
@click.argument("target_path", type=click.Path(exists=True))
@click.option("--provider", "-p", default=None, help="LLM provider: gemini, groq, ollama, openai, mock")
@click.option("--output", "-o", default=None, help="Save PR comment Markdown to a file.")
@click.option("--apply", is_flag=True, help="Apply the verified patch directly to the target file.")
@click.option("--max-retries", default=3, help="Maximum self-healing reflection iterations.")
def review(target_path: str, provider: str, output: str, apply: bool, max_retries: int):
    """Review a Python file, synthesize tests, and verify a self-healing patch."""
    console.print(BANNER)
    target = Path(target_path)

    if target.is_dir():
        console.print(f"[bold yellow]Scanning directory:[/bold yellow] {target}")
        py_files = list(target.glob("**/*.py"))
        if not py_files:
            console.print("[red]No Python (.py) files found in directory.[/red]")
            return
        target = py_files[0]
        console.print(f"[cyan]Selected target file:[/cyan] {target}")

    source_code = target.read_text(encoding="utf-8")

    active_provider = provider or Config.resolve_provider()
    console.print(f"[bold green]Active LLM Provider:[/bold green] [magenta]{active_provider.upper()}[/magenta]")
    console.print(f"[bold green]Target File:[/bold green] {target.resolve()}\n")

    orchestrator = SupervisorOrchestrator(
        llm=LLMProvider(active_provider),
        max_repair_attempts=max_retries
    )

    with console.status("[bold green]PatchPilot Committee working...", spinner="dots") as status:
        def update_status(stage: str, msg: str):
            status.update(f"[bold cyan][{stage.upper()}][/bold cyan] {msg}")

        state = orchestrator.run_review(
            source_code=source_code,
            filepath=target.name,
            progress_callback=update_status
        )

    # 1. Display Audit Findings Table
    if state.audit_report and state.audit_report.issues:
        table = Table(title="[AUDIT] Detected Code Flaws & Security Risks", show_lines=True)
        table.add_column("Severity", justify="center", style="bold")
        table.add_column("Line", justify="center", style="cyan")
        table.add_column("Issue", style="white")
        table.add_column("CWE", justify="center", style="dim")
        table.add_column("Suggested Fix", style="green")

        for issue in state.audit_report.issues:
            sev_color = {
                "CRITICAL": "[bold red]CRITICAL[/bold red]",
                "HIGH": "[red]HIGH[/red]",
                "MEDIUM": "[yellow]MEDIUM[/yellow]",
                "LOW": "[blue]LOW[/blue]",
            }.get(issue.severity.upper(), issue.severity)

            table.add_row(
                sev_color,
                str(issue.line_number or "-"),
                issue.title,
                issue.cwe_id or "-",
                issue.suggested_fix
            )
        console.print(table)
    else:
        console.print(Panel("[bold green][OK] No critical flaws detected by Auditor Agent![/bold green]"))

    # 2. Display Sandbox Verification Summary
    status_style = "bold green" if state.is_verified else "bold red"
    status_text = "PASSED & VERIFIED" if state.is_verified else "FAILED (Needs manual triage)"
    
    summary_panel = Panel(
        f"[bold]Verification Status:[/bold] [{status_style}]{status_text}[/{status_style}]\n"
        f"[bold]Self-Healing Attempts:[/bold] {state.repair_attempts}/{max_retries}\n"
        f"[bold]Patch Explanation:[/bold] {state.current_patch.patch_explanation if state.current_patch else 'None'}",
        title="[SANDBOX EXECUTION REPORT]",
        border_style="green" if state.is_verified else "red"
    )
    console.print(summary_panel)

    # 3. Display Diff
    if state.current_patch and state.current_patch.patched_code != source_code:
        console.print("\n[bold cyan][PATCH] Proposed Code Diff:[/bold cyan]")
        diff = list(difflib.unified_diff(
            source_code.splitlines(keepends=True),
            state.current_patch.patched_code.splitlines(keepends=True),
            fromfile=f"a/{target.name}",
            tofile=f"b/{target.name}"
        ))
        diff_str = "".join(diff)
        if diff_str.strip():
            console.print(Syntax(diff_str, "diff", theme="monokai", line_numbers=False))

    # 4. Save Output if requested
    pr_markdown = MarkdownReportBuilder.build_pr_comment(state)
    if output:
        out_path = Path(output)
        out_path.write_text(pr_markdown, encoding="utf-8")
        console.print(f"[bold green]PR review report written to:[/bold green] {out_path.resolve()}")

    # 5. Apply patch if requested
    if apply and state.is_verified and state.current_patch:
        target.write_text(state.current_patch.patched_code, encoding="utf-8")
        console.print(f"[bold green]Patch successfully applied to:[/bold green] {target.resolve()}")


@main.command()
@click.argument("target_path", type=click.Path(exists=True))
def inspect(target_path: str):
    """Inspect the AST structure and cyclomatic complexity of a Python file."""
    console.print(BANNER)
    target = Path(target_path)
    source_code = target.read_text(encoding="utf-8")

    report = CodeInspector.inspect_code(source_code, filepath=target.name)

    if not report.syntax_valid:
        console.print(Panel(f"[bold red]Syntax Error:[/bold red] {report.syntax_error}", title="AST Error"))
        return

    table = Table(title=f"[AST] Structural Analysis: {target.name}", show_lines=True)
    table.add_column("Type", style="cyan")
    table.add_column("Identifier", style="bold white")
    table.add_column("Lines", justify="center")
    table.add_column("Complexity", justify="center", style="magenta")
    table.add_column("Signature / Details", style="dim")

    for cls in report.classes:
        table.add_row(
            "CLASS",
            cls.name,
            f"{cls.start_line}-{cls.end_line}",
            "-",
            f"Bases: {', '.join(cls.bases) if cls.bases else 'object'} | Methods: {len(cls.methods)}"
        )

    for fn in report.functions:
        ret = f" -> {fn.return_type}" if fn.return_type else ""
        table.add_row(
            "ASYNC FN" if fn.is_async else "FUNCTION",
            fn.name,
            f"{fn.start_line}-{fn.end_line}",
            str(fn.complexity),
            f"({', '.join(fn.args)}){ret}"
        )

    console.print(table)
    console.print(f"[dim]Total Lines: {report.total_lines} | Average Function Complexity: {report.average_complexity}[/dim]\n")


@main.command()
def doctor():
    """Diagnose environment, Python version, git, and LLM provider credentials."""
    console.print(BANNER)
    console.print("[bold yellow][*] Running PatchPilot Doctor Diagnostics...[/bold yellow]\n")

    table = Table(title="System & LLM Readiness", show_lines=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    # Python version
    py_ver = sys.version.split()[0]
    table.add_row("Python", "[green]OK[/green]", f"v{py_ver}")

    # Gemini
    gemini_status = "[green]Configured[/green]" if Config.GEMINI_API_KEY else "[yellow]Missing[/yellow]"
    table.add_row("Google Gemini API", gemini_status, "GEMINI_API_KEY")

    # Groq
    groq_status = "[green]Configured[/green]" if Config.GROQ_API_KEY else "[yellow]Missing[/yellow]"
    table.add_row("Groq Cloud API", groq_status, "GROQ_API_KEY")

    # OpenAI
    openai_status = "[green]Configured[/green]" if Config.OPENAI_API_KEY else "[yellow]Missing[/yellow]"
    table.add_row("OpenAI API", openai_status, "OPENAI_API_KEY")

    # Ollama
    table.add_row("Local Ollama", "[cyan]Available[/cyan]", f"Host: {Config.OLLAMA_BASE_URL}")

    # Fallback
    table.add_row("Simulated Mock Mode", "[green]Ready[/green]", "Built-in zero-key fallback for offline runs")

    console.print(table)
    console.print("\n[bold green]System is ready to run reviews![/bold green]")
    console.print("To run a test review: [bold cyan]patch-pilot demo[/bold cyan]\n")


@main.command()
def demo():
    """Run an immediate self-healing demonstration on a bundled buggy module."""
    demo_file = Path("examples") / "buggy_data_processor.py"
    if not demo_file.exists():
        console.print("[red]Demo file examples/buggy_data_processor.py not found.[/red]")
        return

    console.print("[bold cyan][*] Launching instant demonstration on buggy_data_processor.py...[/bold cyan]")
    ctx = click.get_current_context()
    ctx.invoke(review, target_path=str(demo_file), provider="mock", output="demo_pr_review.md", apply=False, max_retries=3)


if __name__ == "__main__":
    main()
