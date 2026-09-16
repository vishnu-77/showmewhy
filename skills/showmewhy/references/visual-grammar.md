# ShowMeWhy visual grammar

Use the smallest representation that makes structure easier to understand than prose.

## Cause / evidence

```text
change
  │
  ▼
observed effect
  │
  ▼
conclusion
```

Use branching only when distinct evidence streams materially support or contradict the conclusion.

## Comparison

Use a Markdown table. Keep dimensions decision-relevant and avoid repeating prose below it.

## Timeline

```text
09:12 build
   ↓
09:14 deploy
   ↓
09:16 errors begin
```

Use only when order or temporal proximity matters.

## Hierarchy

```text
system
├── api
├── worker
└── database
```

## Distribution

```text
PASS  ████████████████ 421
FAIL  █                  5
SKIP  █                  2
```

Do not imply precise area/length encoding when the bars are only illustrative. Counts remain authoritative.

## Architecture / dependencies

Use ASCII for small graphs. Use Mermaid only when more than a few relationships make ASCII difficult to scan.

## No visual

Prefer plain text when the answer is:

- a single fact
- a single instruction
- a short correction
- a simple yes/no with one caveat

The absence of a visual is a valid ShowMeWhy decision.
