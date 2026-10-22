# Provider prompt delivery audit — 20 October 2026

The audit found real delivery gaps. Spider-AI sent the profile system instruction, extraction prompt and field descriptions, but omitted `parse_prompt`. LlamaCloud's ordinary and selected-field extraction omitted `system_instruction`. Selected-field extraction also omitted the current parser guidance. Learned region guidance was wired only to ordinary LlamaCloud processing.

The running configuration is version 32, using Spider-AI with sequential page extraction enabled. It submits image-based chat-completion requests to the configured Spider gateway, using model `pct-prod-spider/pecut/gemini-3.8-flash-high`. All 12 active document profiles passed the read-only prompt compilation audit. The updated API, worker and frontend have been built and started locally; no profile text needed to be republished for this runtime delivery fix.

## Current delivery contract

| Active input | Spider-AI ordinary / multipage | Spider-AI selected fields | LlamaCloud ordinary | LlamaCloud selected fields |
| --- | --- | --- | --- | --- |
| `system_instruction` | System message on every request | System message on every page | Parser custom prompt and extraction system prompt | Extraction system prompt |
| `parse_prompt` | Explicit parser/layout reading section | Same reading section | Parser custom prompt and extraction reading section | Extraction reading section |
| `system_prompt` | Profile extraction section | Profile extraction section | Extraction system prompt | Extraction system prompt |
| Root, field and nested descriptions | Path-indexed guidance | Selected schema descriptions, including nested children | `data_schema` | Selected `data_schema` |
| Request-specific reread instruction | Not applicable | System task instruction | Not applicable | Extraction task instruction |
| Compatible learned location hints | Reading guidance | Reading guidance restricted to selected fields | Parser and extraction guidance | Extraction guidance restricted to selected fields |
| Classification descriptions | Separate classifier request | Known document type retained | Separate classification rules | Known document type retained |

Prompt assembly is shared in `backend/app/extraction_prompts.py`. Saved text is included without prompt truncation. Parser notes are explicitly scoped as reading guidance during extraction so a parser-format instruction does not change the extraction JSON contract. Sequential extraction retains the entire base prompt on every physical page and adds only that page's images and continuity context. Enlarged views supplement the original page. Request size accounting includes the additional parser text; oversize requests fail before submission instead of silently dropping prompts.

Only the active published/pinned profile is used. Saved named versions are inactive until loaded and published. Classification descriptions belong to classification; an explicitly confirmed type skips that stage. Display labels and validation policies are application settings, not model prompts. Synthetic fixture mode performs no model extraction.

## Retries, prompt changes and evidence

New provider submissions record a hash manifest for the system instruction, parser prompt, extraction prompt, applicable schema/descriptions, request-specific guidance and any location guidance. Spider-AI also records the exact serialized request hash and retains the existing image-redacted request preview. Ordinary extraction metadata and selected-field request history expose the recorded prompt receipt.

A cached response with a recorded, different prompt manifest is rejected with directions to create a new field reread. It does not trigger a new paid call automatically. Older cached responses without a manifest remain available for recovery and are marked `LEGACY_OR_UNRECORDED`; they are never presented as proof that today's prompts were used.

Ordinary Retry resumes a saved submission or processes stored raw values; it is not a new model call. Revalidation also uses stored values. To run changed published prompts against an existing document, start selected-field reprocessing with **Use latest configuration** enabled. The request captures a configuration snapshot, so publishing again while it is running does not change its instructions midway.

LlamaCloud selected-field extraction still reuses the saved parse job. Its extractor receives all current profile instructions, but it does not rerun OCR/parser execution. A change that requires recovering text missing from that saved parse needs a new document-processing run. Spider-AI selected-field extraction rereads the original page images.

## Verification scope

Tests inspect outgoing HTTP JSON for Spider-AI and outgoing SDK arguments for LlamaCloud, rather than only checking helper return values. They cover single-request extraction, sequential page requests, selected fields, nested descriptions, request guidance, saved prompt receipts, cache reuse, prompt-change rejection, learned location scope and legacy cache labeling. Transport is mocked and the test container has no network, so no paid provider calls occur.

Final results: **40 backend tests passed**, including the prompt-delivery suite. The six focused prompt-delivery tests also passed after adding an explicit nested-array-description check. **12 browser checks passed**, with no browser errors or paid model calls. The frontend production build passed, the API health check returned `ok`, and the four running provider source files match the workspace hashes. No production document jobs were active at the final check.

This proves delivery of the configured instructions from the application to its provider boundary. It does not establish whether an upstream gateway rewrites messages or whether a model follows every instruction. This release does not resolve or relabel the previously observed Poko `Al`/`AI`/`A1` handwriting failure. Accuracy evidence remains separate from prompt-delivery evidence.
