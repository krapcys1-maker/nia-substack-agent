# Execution, costs and publication quality

NIA runs unattended after setup. Each operation has a deadline, each API attempt
has a ledger entry, and each publication needs an eligible result. A deferred
material does not become an instruction to publish it on the next retry.

## Provider calls and budgets

The ledger distinguishes `pending`, `known`, `unknown` and historical `legacy`
usage. `price_verified` separately records whether the price is reconciled with
billing; a published price is not an invoice. Each new attempt includes an
operation identifier, attempt number, pricing version and source.

Before a request, a SQLite transaction reserves its estimated maximum cost.
The output limit is reduced to fit the available budget. Other processes using
that database see the reservation. Successful usage releases it and replaces it
with the computed cost. Unknown usage retains exposure instead of pretending
the request was free. Do not automatically clear unknown reservations: reconcile
them with the provider's records first. Existing records are not silently repriced.

Search tools can consume additional internal context. Their reserved input is
an estimate, so this is not a provider-enforced spending cap. Different NIA
instances have separate databases; their limits do not combine into an account
wide provider limit. Use the provider's own account controls for that boundary.

Provider timeouts measure connection or read inactivity. NIA also imposes a
deadline on the whole operation, including retries and search recovery. The
transport worker cannot write the database. If it fails to stop immediately,
the caller still returns on time, records the uncertainty and closes the stream.
Remote cancellation does not guarantee that the provider stopped billing.

Browser source reads run in an owned subprocess and save each page as it
finishes. A deadline covers navigation and shutdown; a stuck child is stopped
while completed pages remain available. This does not terminate an attached
user Chrome process. Publishing actions are not retried by this read worker.

DeepSeek Chat Completions and Responses both receive `DEEPSEEK_EFFORT`.
Previously only Responses received it, so ordinary chat used the provider's
default high effort even when NIA was configured for low effort. Mechanical
roles continue to disable thinking explicitly.

Rates are identified by `config.PRICING_VERSION` and `PRICING_SOURCES`.
DeepSeek peak hours account for weekdays and UTC. Claude cache reads and writes
have separate usage fields. Image pricing uses returned token usage when present,
and otherwise reports an estimate for the requested size and quality.

## Publication decisions

Immediately before an account action, NIA checks the logged-in user against
the configured public account, including its stable identifier. Its brief
identity cache is tied to the browser context and session cookie fingerprint.
An unavailable identity check cannot grant permission to publish.

Style observations remain advisory. A refuted, outdated or unsupported factual
claim makes the material ineligible until repaired. A nonnumeric factual claim
still needs evidence. A check that did not complete is recorded as unknown.
Repairs use the existing per-run quota, pass the content checks and undergo
verification again. A new unsupported claim is not accepted in exchange for
removing an old one. An unsuccessful article remains saved, with its reason.
Paid repair candidates and their checks remain in the private `repair-attempts`
directory, including when verification fails. They are diagnostic drafts and
are never treated as a publication queue.

The article reviewer returns one compact decision per numbered text segment.
NIA reconstructs the original text locally and rejects missing or duplicate
identifiers. This preserves coverage without asking the model to copy the article.

## Reusing work

Stage cache keys include inputs, preset, models, prompt/code version and relevant
arguments. Entries expire and are written atomically. Older incompatible cache
files are ignored. Identical successful fact checks can be reused briefly for
the same text, context, model, policy and day; edits require another decision.
This is deliberately narrower than inferring that a different claim is already
verified. Daily and standalone article entry points share the same instance lock.

## Validation

`test_runtime_contract.py` exercises interrupted streams, missing usage, retries,
reservation visibility, cancellation, cache accounting and image usage offline.
`test_quality_contract.py` exercises unsupported claims, failed checks, unsafe
repairs, cache invalidation and authenticated identity. Article publication tests
verify both the saved-but-deferred path and the checked-before-publishing path.

These tests complement live acceptance runs. They do not guarantee uninterrupted
access to a provider or Substack, nor prove that every generated text is correct.
Public presets retain their production model choices; cheaper model variants
should earn promotion through measured editorial comparisons.
