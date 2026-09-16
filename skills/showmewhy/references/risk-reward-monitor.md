# Legacy risk / reward monitor

The per-run `REWARDED / CONSTRAINED` token-budget monitor was retired in ShowMeWhy 4.2.0 because it added noise to the default verification surface.

Current session-level monitor semantics live in [`session-monitor.md`](session-monitor.md). Token/context/CO₂e accounting is available through explicit `impact` mode.
