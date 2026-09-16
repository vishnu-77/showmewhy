#!/usr/bin/env python3
"""Estimate ShowMeWhy token reduction and operational CO2e equivalence.

The default energy/carbon profile is intentionally labelled LOW confidence.
Pass runtime-specific values for more meaningful estimates.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

DEFAULT_WH_PER_1K_OUTPUT = 1.11
DEFAULT_PUE = 1.20
DEFAULT_GRID_G_PER_KWH = 400.0
DEFAULT_TREE_KG_PER_YEAR = 60.0


def estimate_tokens(text: str) -> int:
    """Rough fallback token estimate. Prefer host-provided counts."""
    if not text:
        return 0
    return max(1, math.ceil(len(text.encode("utf-8")) / 4))


def calculate(
    source_tokens: int,
    output_tokens: int,
    budget: int = 300,
    wh_per_1k_output: float = DEFAULT_WH_PER_1K_OUTPUT,
    pue: float = DEFAULT_PUE,
    grid_g_per_kwh: float = DEFAULT_GRID_G_PER_KWH,
    tree_kg_per_year: float = DEFAULT_TREE_KG_PER_YEAR,
    basis: str = "presentation",
) -> dict:
    if source_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    if budget <= 0:
        raise ValueError("budget must be positive")
    if wh_per_1k_output < 0 or pue <= 0 or grid_g_per_kwh < 0 or tree_kg_per_year <= 0:
        raise ValueError("energy/carbon parameters must be non-negative and denominators positive")

    reduced = max(source_tokens - output_tokens, 0)
    reduction_pct = (reduced / source_tokens * 100.0) if source_tokens else 0.0
    budget_pct = output_tokens / budget * 100.0

    energy_wh = (reduced / 1000.0) * wh_per_1k_output * pue
    co2e_g = (energy_wh / 1000.0) * grid_g_per_kwh

    tree_g_per_year = tree_kg_per_year * 1000.0
    tree_years = co2e_g / tree_g_per_year if tree_g_per_year else 0.0
    tree_minutes = tree_years * 365.0 * 24.0 * 60.0

    realised = basis in {"pre-generation", "hook"}
    carbon_label = (
        "estimated_operational_co2e_avoided_g"
        if realised
        else "estimated_operational_co2e_equivalent_g"
    )

    result = {
        "source_tokens": source_tokens,
        "output_tokens": output_tokens,
        "reduced_tokens": reduced,
        "reduction_pct": round(reduction_pct, 2),
        "budget_tokens": budget,
        "budget_utilisation_pct": round(budget_pct, 2),
        "within_budget": output_tokens <= budget,
        "basis": basis,
        "realised_avoidance_claim": realised,
        "energy_profile": {
            "wh_per_1k_output_tokens": wh_per_1k_output,
            "pue": pue,
            "grid_carbon_intensity_g_per_kwh": grid_g_per_kwh,
            "tree_sequestration_kg_co2_per_year": tree_kg_per_year,
            "estimate_quality": "LOW",
        },
        "estimated_energy_equivalent_wh": round(energy_wh, 6),
        carbon_label: round(co2e_g, 6),
        "tree_time_equivalent_minutes": round(tree_minutes, 4),
    }
    return result


def read_text(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group()
    source.add_argument("--source-tokens", type=int)
    source.add_argument("--source-file")
    output = p.add_mutually_exclusive_group()
    output.add_argument("--output-tokens", type=int)
    output.add_argument("--output-file")
    p.add_argument("--budget", type=int, default=300)
    p.add_argument("--wh-per-1k-output", type=float, default=DEFAULT_WH_PER_1K_OUTPUT)
    p.add_argument("--pue", type=float, default=DEFAULT_PUE)
    p.add_argument("--grid-g-per-kwh", type=float, default=DEFAULT_GRID_G_PER_KWH)
    p.add_argument("--tree-kg-per-year", type=float, default=DEFAULT_TREE_KG_PER_YEAR)
    p.add_argument(
        "--basis",
        choices=["presentation", "pre-generation", "hook"],
        default="presentation",
        help="presentation is counterfactual equivalence; pre-generation/hook may represent realised avoidance",
    )
    p.add_argument("--json", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()

    source_text = read_text(args.source_file)
    output_text = read_text(args.output_file)

    source_tokens = args.source_tokens
    if source_tokens is None:
        source_tokens = estimate_tokens(source_text or "")

    output_tokens = args.output_tokens
    if output_tokens is None:
        output_tokens = estimate_tokens(output_text or "")

    result = calculate(
        source_tokens=source_tokens,
        output_tokens=output_tokens,
        budget=args.budget,
        wh_per_1k_output=args.wh_per_1k_output,
        pue=args.pue,
        grid_g_per_kwh=args.grid_g_per_kwh,
        tree_kg_per_year=args.tree_kg_per_year,
        basis=args.basis,
    )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    carbon_key = (
        "estimated_operational_co2e_avoided_g"
        if result["realised_avoidance_claim"]
        else "estimated_operational_co2e_equivalent_g"
    )
    carbon_label = (
        "Est. operational CO2e avoided"
        if result["realised_avoidance_claim"]
        else "Est. operational CO2e equivalent"
    )

    print(f"ShowMeWhy · {result['output_tokens']} / {result['budget_tokens']} tokens · ↓ {result['reduction_pct']:.1f}%")
    print(f"Reduced tokens · {result['reduced_tokens']}")
    print(f"{carbon_label} · {result[carbon_key]:.4f} g*")
    print(f"Tree-time equivalent · {result['tree_time_equivalent_minutes']:.2f} min*")
    print("* LOW-confidence reference profile unless runtime-specific values are supplied.")
    if not result["realised_avoidance_claim"]:
        print("  Presentation basis: this is an equivalence, not retroactive emissions avoided.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
