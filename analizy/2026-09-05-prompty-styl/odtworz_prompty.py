"""Odtworzenie wejsc pisarzy bez sieci, modeli i danych produkcyjnych.

Uruchom z korzenia repo: python analizy/2026-09-05-prompty-styl/odtworz_prompty.py
Scenariusze sa syntetyczne. Brakujace przyklady stylu NIE sa zastepowane proza.
To pomiar kontraktow promptow, nie eksperyment jakosci generowanych tekstow.
"""
from __future__ import annotations

import json
import hashlib
import pathlib
import sys
import tempfile
from datetime import date, timedelta
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / "odtworzone"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "agent-v2"))
sys.argv = [str(ROOT / "agent-v2/tests/test_prompt_audit.py")]
import config

config.W_TESCIE = True
config.WOLNO_WOLAC_MODEL = False
config.WOLNO_TKNAC_PRODUKCYJNA_BAZE = False


class Przechwycony(BaseException):
    pass


def main():
    with tempfile.TemporaryDirectory(prefix="nia-prompt-audit-") as tmp:
        stare = config.uzyj_katalogu_danych(pathlib.Path(tmp))
        try:
            import stages
            import style
            import llm
            import gates

            # Neutralna tozsamosc; nie zapisujemy lokalnych danych konta.
            config.NAZWA_MARKI = "Example Publication"
            config.NISZA = "how technology works"
            config.KAT_REDAKCYJNY = "explain what changes for the reader"
            config.ARTICLE_LANGUAGE = "English"
            stages.WRITER_SYSTEM = (
                "You write for the anonymous editorial brand Example Publication. "
                "You assert only what the supplied evidence card establishes. "
                "Return exactly one JSON object, with no Markdown fence and no prose around it."
            )
            facts = {"fact": {"fact": "Synthetic material with no quantity or comparison.",
                               "url": "https://example.invalid/source"}}
            captures = []
            examples = style.load_examples()

            def capture(purpose, system, user, **kwargs):
                captures.append({"purpose": purpose, "system": system, "user": user})
                raise Przechwycony()

            summary = {"method": "Interception before llm.call transport; synthetic inputs; no generation",
                       "prompts": [], "missing_style_examples": not (config.STYLE_CORPUS.parent / "przypiecia.json").exists()}

            def run(name, fn):
                try:
                    fn()
                except Przechwycony:
                    record = captures[-1]
                    saved_user = record["user"]
                    for example in examples:
                        saved_user = saved_user.replace(example["text"], "[LOCAL STYLE EXAMPLE: " + example["function"] + "; text omitted from report]")
                    (OUT / (name + ".txt")).write_text(
                        "SYSTEM\n" + record["system"] + "\n\nUSER\n" + saved_user, encoding="utf-8")
                    summary["prompts"].append({"scenario": name, "purpose": record["purpose"],
                                               "system_words": len(record["system"].split()),
                                               "user_words": len(record["user"].split()),
                                               "user_chars": len(record["user"]),
                                               "no_emphasis_on_tokens": "word count, not provider tokens"})

            with patch.object(llm, "call", capture), patch.object(stages, "ostatnie_otwarcia", return_value=[]), \
                 patch.object(stages, "teksty_ostatnich_notek", return_value=[]):
                for kind, form in [("CIEKAWOSTKA", "PROSTA"), ("CIEKAWOSTKA", "LISTA"),
                                   ("MYSL", "LICZBA"), ("MYSL", "LISTA"), ("DYSKUSJA", "PYTANIE")]:
                    with patch.object(config, "losowy_ksztalt_mysli", return_value="TEZA"):
                        material = {"nie_cytuj_tego": "Synthetic context only; no factual evidence."} if kind == "MYSL" else facts
                        run(kind + "_" + form, lambda kind=kind, form=form, material=material:
                            stages.note(None, 0, kind, material, note_form=form))
                with patch.object(config, "losowe_otwarcie", return_value=config.OTWARCIA[4]), \
                     patch.object(config, "losowa_postawa", return_value=("CIEKAWOSC", config.POSTAWY_KOMENTARZA["CIEKAWOSC"][1])), \
                     patch.object(config, "losowa_dlugosc", return_value=12):
                    run("komentarz_ciekawosc_sprzeciw", lambda: stages.comment_on(None, 0, {
                        "author": "Example Author", "title": "Synthetic example", "text": "A synthetic observation."}))
                with patch.object(config, "losowe_otwarcie", return_value=config.OTWARCIA[1]), \
                     patch.object(config, "losowa_dlugosc", return_value=12):
                    run("odpowiedz_pytanie", lambda: stages.reply_to(None, 0, {
                        "author": "Reader", "under": "article", "text": "What did the article establish?"}, {}))
                with patch.object(style, "load_examples", return_value=[]), \
                     patch.object(stages, "ostatnie_uwagi", return_value=""), \
                     patch.object(config, "losowy_ruch_koncowy", return_value=("GDYBY_INACZEJ", config.RUCHY_KONCOWE["GDYBY_INACZEJ"])), \
                     patch.object(config, "losowa_liczba_paraleli", return_value=(1, config.OPIS_LICZBY_PARALELI[1])):
                    run("artykul_THIN_bez_probek", lambda: stages.write(None, 0, {
                        "working_thesis": "Synthetic finding.", "confirmed_claims": [],
                        "citable_numbers": [], "parallel_mechanisms": []}, "THIN"))
                with patch.object(stages, "ostatnie_uwagi", return_value=""), \
                     patch.object(config, "losowy_ruch_koncowy", return_value=("GDYBY_INACZEJ", config.RUCHY_KONCOWE["GDYBY_INACZEJ"])), \
                     patch.object(config, "losowa_liczba_paraleli", return_value=(1, config.OPIS_LICZBY_PARALELI[1])):
                    run("artykul_THIN_z_probkami", lambda: stages.write(None, 0, {
                        "working_thesis": "Synthetic finding.", "confirmed_claims": [],
                        "citable_numbers": [], "parallel_mechanisms": []}, "THIN"))

            summary["MYSL_formy_8_dni"] = []
            idx = config.NOTE_MIX_OTHER_DAY.index("MYSL")
            for offset in range(8):
                day = date(2026, 9, 5) + timedelta(days=offset)
                form = config.NOTE_FORM_MIX[(day.timetuple().tm_yday + idx) % len(config.NOTE_FORM_MIX)]
                summary["MYSL_formy_8_dni"].append({"day": str(day), "form": form})
            summary["uwaga_gestosci"] = gates.uwagi_z_formy({
                "beliefs": [{"belief": "one"}, {"belief": "two"}],
                "reader_moment": {"quote": "synthetic"}}, "word " * 650)
            summary["wymagane_przekonania_przy_celu"] = {
                kind: (settings["cel"] + config.SLOW_NA_BEAT - 1) // config.SLOW_NA_BEAT
                for kind, settings in config.DLUGOSC_WG_GLEBOKOSCI.items()}
            summary["style_file_words"] = {
                path.name: len(path.read_text(encoding="utf-8").split())
                for path in (ROOT / "style-profiles").glob("*.md")}
            summary["local_style_examples"] = [{"function": e["function"], "words": len(e["text"].split()),
                                                  "chars": len(e["text"])} for e in examples]
            summary["NOTE_MIX_OTHER_DAY"] = config.NOTE_MIX_OTHER_DAY
            summary["source_sha256"] = {
                str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in [ROOT / "agent-v2/stages.py", ROOT / "agent-v2/config.py", ROOT / "agent-v2/style.py",
                             ROOT / "agent-v2/gates.py", *sorted((ROOT / "agent-v2/prompts").glob("*.md")),
                             *sorted((ROOT / "style-profiles").glob("*.md"))]}
            (OUT / "pomiar.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        finally:
            config.przywroc_katalog_danych(stare)


if __name__ == "__main__":
    main()
