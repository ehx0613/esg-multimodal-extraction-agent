# Token Budget

## Goal

The extraction workflow should avoid sending full ESG reports to the LLM. The intended pattern is:

```text
PDF -> text/table preprocessing -> keyword retrieval -> small evidence set -> LLM judgment -> validation
```

## Runtime Controls

The following settings are available in `config/settings.py` and can be overridden through `.env`:

| Setting | Default | Purpose |
| --- | ---: | --- |
| `ROUTE_B_TOP_K` | 4 | Maximum retrieved chunks per qualitative field |
| `ROUTE_B_CHUNK_SIZE` | 800 | Maximum characters per text chunk |
| `ROUTE_B_CHUNK_OVERLAP` | 120 | Overlap between adjacent chunks |
| `MAX_LLM_CALLS_PER_REPORT` | 30 | Hard cap for Route B LLM calls per report |
| `ENABLE_LLM_FOR_QUANTITATIVE` | false | Keep table extraction mostly deterministic |
| `LLM_ONLY_FOR_LOW_CONFIDENCE` | true | Reserve LLM fallback for uncertain fields |
| `CACHE_LLM_RESULTS` | true | Keep repeated runs from paying the same token cost |

## Current Strategy

- Route A handles quantitative indicators and should rely on table OCR, aliases, unit checks, and schema validation first.
- Route B handles qualitative indicators only.
- Each Route B field receives only the top retrieved chunks, not the whole report.
- Route B records `llm_calls` and the active token-budget settings in `route_b_summary.json`.
- Missing or no-text-layer reports should return structured missing values instead of forcing LLM calls.

## Next Improvements

- Persist per-field LLM cache keys based on `report_id`, `field_key`, and retrieved chunk hashes.
- Track approximate prompt characters and response characters per report.
- Add a batch-level token summary to `output/evaluation_summary.csv`.
- Add a stricter retry policy for low-confidence fields only.
