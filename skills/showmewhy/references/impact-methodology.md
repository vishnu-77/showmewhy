# Impact methodology

ShowMeWhy reports token reduction first. Energy and carbon values are secondary estimates and must remain explicitly qualified.

## Claim boundary

There are two different situations.

### Presentation-equivalent reduction

The source text already exists and ShowMeWhy re-presents it more concisely.

The original generation energy has already been consumed. The receipt may estimate the **operational CO₂e equivalent** associated with the token difference, but it must not claim that those historical emissions were actually avoided.

### Realised operational avoidance

A runtime mechanism prevents tokens from being generated or consumed, for example by constraining an initial response or intercepting verbose tool output before it enters model context.

In this case, with a suitable baseline and energy profile, the receipt may report **estimated operational CO₂e avoided**.

## Token accounting

Prefer host-provided token counts.

When unavailable, ShowMeWhy uses a rough fallback of approximately four characters per token. Any count derived this way must be marked with `~`.

```text
reduced_tokens = max(source_tokens - output_tokens, 0)
reduction_pct = reduced_tokens / source_tokens × 100
```

## Reference energy profile

The bundled calculator has a deliberately transparent low-confidence reference profile:

- output energy: **1.11 Wh per 1,000 output tokens**
- PUE: **1.20**
- grid carbon intensity: **400 gCO₂e/kWh**
- tree sequestration reference: **60 kgCO₂/year**

The output-energy coefficient corresponds to approximately 4 joules per output token (`4 J × 1000 / 3600 = 1.11 Wh`). A 2026 review of energy-efficient LLMs cites approximately 4 J/output-token for a 65B-class LLaMA example. This is a reference profile, not a claim about Claude, Codex, GPT, Gemini, or any specific provider deployment.

TokenPowerBench (AAAI 2026) demonstrates why energy/token varies with model, batch size, context length, parallelism, quantisation, and hardware. Provider-specific measurements should replace the reference profile whenever available.

The PUE and grid-intensity values are round reference assumptions, not measurements of the user's serving region. Override them for meaningful operational accounting.

## Energy calculation

For output-token-equivalent reduction:

```text
energy_wh = (reduced_tokens / 1000)
            × wh_per_1k_output_tokens
            × PUE
```

Convert to operational CO₂e:

```text
co2e_g = (energy_wh / 1000)
          × grid_carbon_intensity_g_per_kwh
```

This follows the operational structure used by the Software Carbon Intensity specification:

```text
O = E × I
```

where `E` is operational energy and `I` is location-based carbon intensity.

V0 does not estimate embodied hardware emissions.

## Tree-time equivalent

Tree-time is an optional illustration, not an environmental claim.

```text
tree_time_years = co2e_g / tree_sequestration_g_per_year
```

The reference value of 60 kgCO₂/year is based on an EPA urban-tree equivalency convention. It does **not** mean a literal tree was saved.

## Estimate quality

The bundled default profile is always **LOW** confidence.

Use **MEDIUM** only when a model/hardware-specific benchmark and a relevant carbon-intensity value are supplied.

Use **HIGH** only when runtime energy telemetry and location-relevant carbon intensity are available for the actual workload.

## References

- Niu et al., *TokenPowerBench: Benchmarking the Power Consumption of LLM Inference*, AAAI 2026. DOI: 10.1609/aaai.v40i38.40535
- *Energy-efficient large language models*, Future Generation Computer Systems, 2026. DOI: 10.1016/j.future.2026.108483
- Green Software Foundation, Software Carbon Intensity specification: https://sci.greensoftware.foundation/
- US EPA, Greenhouse Gas Equivalencies Calculator calculations and references: https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator-calculations-and-references
