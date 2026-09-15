from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .common import canonical_json, runtime_root

NODE_TYPES = {"OBSERVATION", "EVIDENCE", "INFERENCE", "CONCLUSION", "CAVEAT", "ARTIFACT", "EVENT", "METRIC", "CHANGE"}
EDGE_TYPES = {"SUPPORTS", "CONTRADICTS", "DERIVED_FROM", "OBSERVED_IN", "VERIFIED_BY", "CORRELATED_WITH", "CAUSED_BY"}


def _id(prefix: str, payload: Any) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def confidence_for_digest(digest: dict[str, Any]) -> str:
    parser = digest.get("parser", {})
    confidence = parser.get("confidence")
    complete = bool(parser.get("complete"))
    if confidence == "high" and complete:
        return "HIGH"
    if confidence == "low" or not complete:
        return "LOW"
    return "MEDIUM"


def build_graph(digest: dict[str, Any]) -> dict[str, Any]:
    run_id = digest["run_id"]
    raw_ref = digest["raw_ref"]
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    raw = {
        "id": _id("node", [run_id, "raw", raw_ref]),
        "type": "ARTIFACT",
        "label": "Retained raw tool output",
        "address": f"{raw_ref}#tool_response",
    }
    observation = {
        "id": _id("node", [run_id, "summary", digest.get("summary")]),
        "type": "OBSERVATION",
        "label": str(digest.get("summary", "")).splitlines()[0][:240] or "Execution summary",
        "address": f"run://{run_id}#summary",
    }
    conclusion = {
        "id": _id("node", [run_id, "status", digest.get("kind"), digest.get("status")]),
        "type": "CONCLUSION",
        "label": f"{digest.get('kind', 'execution')} status: {digest.get('status', 'unknown')}",
        "address": f"run://{run_id}#status",
    }
    nodes.extend([raw, observation, conclusion])
    edges.append({"id": _id("edge", [observation["id"], raw["id"], "DERIVED_FROM"]), "source": observation["id"], "target": raw["id"], "type": "DERIVED_FROM"})
    edges.append({"id": _id("edge", [observation["id"], conclusion["id"], "SUPPORTS"]), "source": observation["id"], "target": conclusion["id"], "type": "SUPPORTS"})

    for idx, finding in enumerate(digest.get("findings") or []):
        node = {
            "id": _id("node", [run_id, "finding", idx, finding]),
            "type": "EVIDENCE",
            "label": str(finding)[:500],
            "address": f"run://{run_id}#findings/{idx}",
        }
        nodes.append(node)
        edges.append({"id": _id("edge", [node["id"], conclusion["id"], "SUPPORTS"]), "source": node["id"], "target": conclusion["id"], "type": "SUPPORTS"})
        edges.append({"id": _id("edge", [node["id"], raw["id"], "OBSERVED_IN"]), "source": node["id"], "target": raw["id"], "type": "OBSERVED_IN"})

    for idx, caveat in enumerate(digest.get("caveats") or []):
        node = {
            "id": _id("node", [run_id, "caveat", idx, caveat]),
            "type": "CAVEAT",
            "label": str(caveat)[:500],
            "address": f"run://{run_id}#caveats/{idx}",
        }
        nodes.append(node)
        edges.append({"id": _id("edge", [node["id"], conclusion["id"], "CONTRADICTS"]), "source": node["id"], "target": conclusion["id"], "type": "CONTRADICTS"})

    graph = {
        "version": "3.0",
        "graph_id": _id("prov", run_id),
        "run_id": run_id,
        "confidence": confidence_for_digest(digest),
        "nodes": nodes,
        "edges": edges,
    }
    validate_graph(graph)
    return graph


def validate_graph(graph: dict[str, Any]) -> None:
    ids = [node.get("id") for node in graph.get("nodes", [])]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate provenance node ids")
    node_ids = set(ids)
    for node in graph.get("nodes", []):
        if node.get("type") not in NODE_TYPES:
            raise ValueError(f"unsupported node type: {node.get('type')}")
        if not str(node.get("address", "")).strip():
            raise ValueError("every provenance node requires an address")
    for edge in graph.get("edges", []):
        if edge.get("type") not in EDGE_TYPES:
            raise ValueError(f"unsupported edge type: {edge.get('type')}")
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            raise ValueError("edge references missing node")
        if edge.get("type") == "CAUSED_BY" and not str((edge.get("meta") or {}).get("causal_basis", "")).strip():
            raise ValueError("CAUSED_BY requires explicit causal_basis")


def persist_graph(graph: dict[str, Any], cwd: str | Path | None = None) -> Path:
    root = runtime_root(cwd) / "provenance"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{graph['run_id']}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def load_graph(run_id: str, cwd: str | Path | None = None) -> dict[str, Any]:
    return json.loads((runtime_root(cwd) / "provenance" / f"{run_id}.json").read_text(encoding="utf-8"))
