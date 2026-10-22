# Reusable extraction rules — 20 October 2026

The reviewer notes are reusable extraction requirements, not a list of expected answers to insert into model output. Release `field-quality-v8-profile-rules` is built and running locally. Published configuration version 32 contains the current rules.

## Configuration

Open Settings, choose a document profile, then edit Document instructions and its field descriptions. The published system instruction contains the shared reading rules; field descriptions define label aliases, scope, continuation lines, presence types, and applicable invoice roles. The extraction request sends both levels of instructions.

Extraction consistency exposes sampling variation and the supported same-case address reconciliation switch. Advanced profile policy contains up to three configurable enlarged original-page regions. Both normal extraction and field reprocessing use these regions and the saved sampling settings. This improves repeatability but does not guarantee correct interpretation of ambiguous handwriting.

New cases use the latest published configuration. Existing cases keep their pinned configuration for reproducibility. To apply these improvements to an existing document, use selected-field reprocessing with **Use latest configuration** enabled (the default); publish profile edits before submitting the request. A one-time request note alone is not a reusable profile rule.

## Behavior implemented

- Separate entered names from autographs, read recipient and charge continuation lines, preserve item and bank roles, and distinguish handwritten glyphs without borrowing sample answers.
- Send enlarged regions during ordinary extraction as well as selected-field rereads; preserve the original full page.
- Use profile-controlled temperature and top-p in both paths. The published default is temperature 0 and top-p 1.
- For the Valas declaration, an explicit policy can reconcile a near-identical customer address against an uncorrected LLD payer address in the same case, organization and branch. All numeric address tokens and attached suffixes must agree. Conflicting sources, source reviewer overrides and target reviewer overrides prevent replacement. The original observation and source document remain traceable. Source completion can revalidate dependent documents regardless of processing order.
- Keep reference corrections, display fixes, raw model observations and reviewer corrections distinct. Incorrect sample references must not train the extractor to contradict the original document.

## Actual verification and remaining issue

Fresh replay cases used new document IDs, empty raw values and overrides, and no cached extraction responses. The original PDFs were reused. Document classification was confirmed so these tests exercise the ordinary extraction pipeline rather than classification. Expected values were used only after extraction for scoring. Replays ran against an isolated database and did not replace the reviewed production documents.

Configuration 30: two fresh runs each passed Bayu's declaration address and Poko's bank signature; Poko's address prefix failed both times (`AI` instead of the reviewer-confirmed `Al`). Configuration 31, with a tighter address view, again passed the signature but read the prefix as `AI` and then `A1`. Configuration 32 adds shared system-level glyph guidance; its fresh run passed the signature and still returned `A1` for the prefix.

Thus the previous 40/40 workbook is a **reviewed effective-value result**, not proof of automatic 100% accuracy. Poko's address still requires its audited reviewer correction. No sample-specific `Al` replacement or equivalence rule was introduced. The latest test does not establish automatic compliance for all 40 fields or for unseen documents.

`Published_Profile_Rules.json` exports the published prompts and policies. `Reviewer_Rule_Coverage.json` maps all 40 notes to the saved field rule and distinguishes reference/display corrections. `Pristine_Extraction_Evidence.json` contains all 12 scored observations across configurations 30–32 (7 valid, 5 invalid; all five failures are the same Poko address prefix). These repeated observations are not a dataset-wide accuracy percentage.

The frontend production build succeeded, and 12 browser checks passed with no browser errors. Backend test results accompany the release evidence.
