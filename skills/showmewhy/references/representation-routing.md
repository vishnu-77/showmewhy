# Representation routing

Verification is **not** rendered as a proof DAG by default. The human verification surface stays compact: result, unresolved material claims, and one next action.

Use a visual only when the **subject matter** becomes easier to understand because of it.

| Information shape | Default | Avoid |
|---|---|---|
| Simple result | text | decorative diagram |
| Verification state | compact `VERIFIED / NEEDS YOU / DO NEXT` surface | arrow chain or evidence graph |
| Claim drill-down | table (`claim · state · witness/gap`) | narrative proof essay |
| Ranked alternatives | table | repeated prose |
| Chronological events | timeline | unordered bullets |
| Distribution / counts | compact bars | chart when two numbers suffice |
| Hierarchy | tree | flat prose |
| Architecture / dependencies | component diagram only when structure matters | oversized Mermaid |
| Comparison | table | parallel paragraphs |
| Uncertainty | explicit OPEN claim + missing obligation | fake confidence percentage |

Routing rule: if the representation takes as much effort to parse as two or three clear lines, use the lines.

Typed provenance may remain available to machines and `why` mode, but it is not the default human UI.
