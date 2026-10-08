# Strategy Resources

These files are runtime method-retrieval resources, not evaluation questions,
reference answers, chat history, or model weights.

- `strategy_meta.json`: reusable strategy cards consumed by the retriever.
- `strategy_lexical_index.json`: BM25/TF-IDF index for the same cards.
- `strategy_lexical_manifest.json`: card digest and index compatibility metadata.

The lexical retriever checks the manifest against the metadata before use.
After intentionally changing strategy cards, rebuild with:

```powershell
python scripts/build_lexical_strategy_index.py
```

The source project identifies its base strategy resource as
ReasonFlux-V2-Template, with supplemental and translated method materials.
The original resource directory's Apache-2.0 declaration is retained in
`strategyrag/README.md`; see the root THIRD_PARTY_NOTICES.md.

Dense embedding arrays, raw datasets, source translation JSONL, and model weights
are not shipped. Optional embedding-maintenance scripts require those inputs
to be supplied separately. Normal Web chat uses the included lexical index.
