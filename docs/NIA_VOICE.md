# Testing NIA's voice

NIA Unfiltered shares one identity across Notes, replies, restacks and articles.
The identity lives in `prompty/linia_redakcyjna.md`; each format adds its own
instructions. Rubrics suggest angles rather than enforcing a mood or sentence
formula. The professional presets keep their own voices.

Evaluate the English original. A translation can strengthen a swear word or
introduce grammatical gender that was absent in English. It is not reliable
evidence of the writer model's exact wording.

To test the **installed** persona, run from the project directory:

```sh
python narzedzia/proba_glosu.py --live --samples 3
```

Use your installation's Python environment (`.venv/bin/python` on Linux or
`.venv\Scripts\python.exe` on Windows). This makes paid calls through the same
Note generator as the scheduler, with its actual sources, memory, models and
prompts. It does not publish or remember the samples as published work. Calls
are recorded as a test run. `--slot 1` selects the second configured Note slot
when one exists. There are no hidden prompt or length overrides.

Read every sample, including the weak ones. Look for a clear point of view,
humour within the observation, adult language, a specific comparison and an
ending that earns its place. Warmth can still sound like NIA. Do not grade by
counting swear words or assume one good example guarantees the next result.

Each paid short-form answer is retained under the private instance's
`persona-drafts` directory with a unique ID, timestamp, preset fingerprint,
exact request, request hash, raw answer and validation status. Repeated inputs
and different models no longer overwrite one another. Confirmed publication
memory links back to the draft ID and request hash. These records include
source and account context; they belong to the private installation, not Git.

The scheduler generates a fresh Note. Running a preview does not queue that
exact wording for publication. Never present a successful preview as proof that
the next independently generated Note will contain the same wording. The saved
request hashes let you distinguish input changes from output variation.

The persona path uses one writing call per attempt. It has no paid stylistic
rewrite or fact-check loop. A malformed or rejected answer is retained for
diagnosis and does not trigger another paid attempt. Articles retain their
separate evidence checks. Unit tests verify text and draft integrity; judging
whether the voice is good still requires reading real outputs.
