# -*- coding: utf-8 -*-
"""Etapy mechaniczne nie placa za myslenie DeepSeeka na glos.

## Po co ten plik istnieje

Zmierzone 2026-09-06 na kartridzu `ai`: modele DeepSeek V4 na
`/chat/completions` rozumuja DOMYSLNIE, a tokeny rozumowania sa liczone jako
wyjscie. Ranking osmiu faktow w banku kosztowal 15 681 tokenow wyjscia, ocena
dziewieciu celow 19 211 — przy odpowiedziach JSON o kilkuset znakach.
Ten sam sedzia z `thinking: disabled`: 138 zamiast 707 tokenow, 1,9 s zamiast
6,1 s (flash), tresc identyczna co do ksztaltu.

Regula: etapy mechaniczne (odsiew, klasyfikacja, ranking, ocena celow,
decyzja o restacku, brief grafiki, rejestr federalny) ida BEZ myslenia; etapy,
ktore pisza albo syntezuja (pisarz, notka, komentarz, synteza, recenzja),
mysla jak dotad. Lista siedzi w `config.DEEPSEEK_BEZ_MYSLENIA`.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_myslenie_deepseeka.py
"""
import ast
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. LISTA ETAPOW BEZ MYSLENIA ===")
bez = set(config.DEEPSEEK_BEZ_MYSLENIA)
for etap in ("feasibility", "classify", "bank", "cele", "restack"):
    sprawdz("etap mechaniczny bez myslenia: %s" % etap, etap in bez)
for etap in ("write", "note", "note_tani", "comment", "reply", "synthesis", "review", "naprawa"):
    sprawdz("etap piszacy/syntezujacy mysli: %s" % etap, etap not in bez)
sprawdz("kazdy etap z listy istnieje w MODEL_FOR", bez <= set(config.MODEL_FOR), bez - set(config.MODEL_FOR))

print()
print("=== 2. TRANSPORT WYSYLA WYLACZNIK TYLKO DLA TYCH ETAPOW ===")
zrodlo = pathlib.Path("agent-v2/llm.py").read_text(encoding="utf-8")
drzewo = ast.parse(zrodlo)
fn = next(w for w in ast.walk(drzewo) if isinstance(w, ast.FunctionDef) and w.name == "_call_deepseek")
tekst_fn = ast.unparse(fn)
sprawdz("_call_deepseek zna wylacznik myslenia", "'thinking'" in tekst_fn and "'disabled'" in tekst_fn)
sprawdz("i uzaleznia go od config.DEEPSEEK_BEZ_MYSLENIA", "DEEPSEEK_BEZ_MYSLENIA" in tekst_fn)
sprawdz("wylacznik jest warunkowy, nie na stale", "if purpose in config.DEEPSEEK_BEZ_MYSLENIA" in tekst_fn)
fn2 = next(w for w in ast.walk(drzewo) if isinstance(w, ast.FunctionDef) and w.name == "_call_deepseek_responses")
sprawdz("kontrdowod: /responses (szukanie w sieci) zostaje z `reasoning.effort`, bez wylacznika",
        "'thinking'" not in ast.unparse(fn2) and "DEEPSEEK_EFFORT" in ast.unparse(fn2))

print()
print("=== 3. SUFIT TOKENOW NADAL MA MIEJSCE NA MYSLENIE TAM, GDZIE ONO ZOSTAJE ===")
sprawdz("write ma zapas na rozumowanie ponad kontrakt",
        config.MAX_TOKENS["write"] > config.THINKING_HEADROOM_TOKENS)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
