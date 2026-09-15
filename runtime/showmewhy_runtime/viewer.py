from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def render_html(graph: dict[str, Any]) -> str:
    nodes = "".join(
        f"<li><strong>{html.escape(str(n['type']))}</strong> — {html.escape(str(n['label']))}<br><code>{html.escape(str(n['address']))}</code></li>"
        for n in graph.get("nodes", [])
    )
    edges = "".join(
        f"<li><code>{html.escape(str(e['source']))}</code> → <strong>{html.escape(str(e['type']))}</strong> → <code>{html.escape(str(e['target']))}</code></li>"
        for e in graph.get("edges", [])
    )
    return f"""<!doctype html><meta charset=\"utf-8\"><title>ShowMeWhy {html.escape(str(graph['run_id']))}</title>
<style>body{{font-family:ui-monospace,SFMono-Regular,monospace;max-width:980px;margin:40px auto;padding:0 20px;line-height:1.5}}code{{word-break:break-all}}li{{margin:12px 0}}h1,h2{{font-family:system-ui,sans-serif}}</style>
<h1>ShowMeWhy provenance</h1><p>Run <code>{html.escape(str(graph['run_id']))}</code> · confidence <strong>{html.escape(str(graph.get('confidence')))}</strong></p>
<h2>Nodes</h2><ol>{nodes}</ol><h2>Edges</h2><ol>{edges}</ol>"""


def write_html(graph: dict[str, Any], output: str | Path) -> Path:
    path = Path(output)
    path.write_text(render_html(graph), encoding="utf-8")
    return path
