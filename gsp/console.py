"""
Output layer — uses rich if available, falls back to click.style.
"""
from __future__ import annotations

try:
    from rich.console import Console as _RichConsole
    from rich.text import Text

    _console = _RichConsole()
    _RICH = True
except ImportError:
    _RICH = False
    _console = None

import click


def success(msg: str) -> None:
    if _RICH:
        _console.print(f"[bold green]✓[/bold green] {msg}")
    else:
        click.echo(click.style("✓ ", fg="green", bold=True) + msg)


def info(msg: str) -> None:
    if _RICH:
        _console.print(f"[bold blue]ℹ[/bold blue] {msg}")
    else:
        click.echo(click.style("ℹ ", fg="blue") + msg)


def warn(msg: str) -> None:
    if _RICH:
        _console.print(f"[bold yellow]⚠[/bold yellow] {msg}")
    else:
        click.echo(click.style("⚠ ", fg="yellow") + msg)


def error(msg: str) -> None:
    if _RICH:
        _console.print(f"[bold red]✗[/bold red] {msg}")
    else:
        click.echo(click.style("✗ ", fg="red", bold=True) + msg)


def step(n: int, total: int, label: str) -> None:
    prefix = f"[{n}/{total}]"
    if _RICH:
        _console.print(f"[dim]{prefix}[/dim] {label}")
    else:
        click.echo(click.style(prefix, dim=True) + " " + label)


def dry_run(msg: str) -> None:
    if _RICH:
        _console.print(f"[dim italic](dry-run) {msg}[/dim italic]")
    else:
        click.echo(click.style(f"(dry-run) {msg}", dim=True))


def rule(title: str = "") -> None:
    if _RICH:
        _console.rule(title)
    else:
        width = 60
        if title:
            pad = (width - len(title) - 2) // 2
            click.echo("─" * pad + f" {title} " + "─" * pad)
        else:
            click.echo("─" * width)
