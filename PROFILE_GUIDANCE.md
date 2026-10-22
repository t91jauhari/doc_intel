# Reusable extraction guidance

When a bank administrator enters Additional extraction guidance in Reprocess
selected fields, Save guidance to this document profile is enabled by default.
Submitting appends the text to that profile's Document Instructions
(`system_instruction`), with the selected field keys recorded as its scope.
The existing instructions remain intact. A new published configuration version
and an audit event record the change. Other profiles are unchanged.

The current request captures the saved configuration and uses it immediately.
New uploads use the published configuration. Existing cases remain pinned to
their original configuration until field reprocessing selects Use latest
published profile instructions. Saving guidance requires that option.

Clearing Save guidance keeps the text local to the request. Users without
configuration publishing permission can use request-only guidance. Historical
requests are not automatically promoted into shared instructions.

Repeated identical guidance for the same fields is not appended twice.
Invalid requests and instructions exceeding the profile's 30,000-character
limit do not publish changes. Saving and queueing occur in one transaction.
Once accepted, the guidance stays published even if the model later fails;
inspect and edit it in Configuration > Document profiles > Document instructions.

Both Spider-AI and LlamaCloud receive the saved instructions through the shared
prompt assembly. Guidance helps the model read the document; it does not insert
expected answers or guarantee a particular extraction value.

Verification: backend persistence, profile isolation, future-upload configuration,
deduplication, authorization, rollback, and provider prompt-delivery tests;
production build and an intercepted browser submission with no paid model call.
