# Record a workflow

See the finished [NIA film and live examples](DEMO.md).

Use a dedicated test publication and a fresh instance. Follow the normal
[installation](INSTALL.md) first: configure your own `.env`, activate a preset,
and establish the browser session. The recording tools are optional; they add
no dependency to the publishing engine.

## Capture the bot's tab

Check the session and the capture before publishing:

```bash
python narzedzia/nagraj_publikacje.py sesja
```

The observer attaches to new tabs opened by the existing bot. It captures the
Substack viewport at 1440 × 900, with timestamps, into
`agent-v2/instancje/<instance>/nagrania/<timestamp>/`. It does not capture the
desktop or other open tabs. API, account, sign-in and settings URLs are excluded.
The recording directory is private runtime data covered by `.gitignore`.

Generate and review your content using the ordinary workflow. Then record a
selected Note result (the JSON returned by `stages.note`, including its
`candidates` array), or an article Markdown file:

```bash
python narzedzia/nagraj_publikacje.py notka --plik /path/to/note.json
python narzedzia/nagraj_publikacje.py artykul --plik /path/to/article.md
```

**Without `--wyslij`, the bot fills the editor but does not press the final
publication button.** This can still create a draft on Substack. Add `--wyslij`
when you intend to publish that content to the active account. For multiple Note
candidates, choose an index with `--kandydat 0` (the default).

Article, Note and comment recording use supplied content. The restack action
generates commentary with the active preset and configured model; that action
can incur model charges. Recording does not enable a scheduler or change
the preset. It delegates publishing to the engine's existing browser functions.
The engine's `DRY_RUN` and activation checks still apply; the recording command
also refuses publication with `KILL_SWITCH=true` or a rejected Note candidate.
Its selected candidate check is not a complete editorial review.

Record other supported actions with the same explicit publication flag:

```bash
python narzedzia/nagraj_publikacje.py komentarz --plik /path/to/comment-result.json --wyslij
python narzedzia/nagraj_publikacje.py polubienie --url https://substack.com/note/c-NOTE_ID --wyslij
python narzedzia/nagraj_publikacje.py restack --url https://substack.com/note/c-NOTE_ID --wyslij
python narzedzia/nagraj_publikacje.py subskrypcja --profil publication-handle --wyslij
```

Comment input contains `target` and `result.candidates`, as returned by the
target-selection and comment stages. Subscription actions select the free
option. An already active subscription is skipped.

Article publishing handles the optional “Publish without buttons” confirmation.
It retries publication reads three times on a separate tab, leaving the editor
available for a delayed confirmation. It does not blindly resend an uncertain
publication. A failed confirmation or missing send button returns an error
and records the saved draft URL in the result. Session expiry and inaccessible
Substack pages still require the underlying access problem to be resolved.

## Review and encode

Inspect the raw images before sharing. A logged-in publishing screen may contain
account information even though the recorder excludes known technical routes.
Select scenes containing the editor and the public result. Do not commit raw
recording folders, `.env`, cookies, API responses, or a whole instance.

Install FFmpeg separately if you want an MP4. The encoder never uses API keys or
connects to Substack:

```bash
python narzedzia/zloz_nagranie.py /path/to/recording demo.mp4
```

Optional `--start 10 --end 35` selects seconds from the capture;
`--speed 2` produces a 2× clip. Pass `--ffmpeg /path/to/ffmpeg` when the binary is
not on PATH. Existing output files are not overwritten.

The recorder captures changed browser frames, with a maximum of roughly six
frames per second. The encoder retains their timing in a 25 fps MP4; it does not
invent intermediate browser actions. Review the complete export, label cuts and
speed changes, and keep claims about costs and completion tied to the actual
run records. A successful HTTP request alone is not a content-quality score.
