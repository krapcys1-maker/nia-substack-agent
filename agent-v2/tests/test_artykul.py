"""Test sciezki artykulu: zaleznosci i nietykanie tego samego tematu."""
import ast
import importlib.util
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import db       # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. KAZDY IMPORT MA POKRYCIE — takze te w srodku funkcji ===")
wlasne = {p.stem for p in pathlib.Path("agent-v2").glob("*.py")}
moduly = set()
for f in pathlib.Path("agent-v2").glob("*.py"):
    for w in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if isinstance(w, ast.Import):
            for a in w.names:
                moduly.add(a.name.split(".")[0])
        elif isinstance(w, ast.ImportFrom) and w.module and w.level == 0:
            moduly.add(w.module.split(".")[0])
zewnetrzne = sorted(m for m in moduly
                    if m not in wlasne and m not in sys.stdlib_module_names)
print("    zewnetrznych modulow: %s -> %s" % (len(zewnetrzne), zewnetrzne))
brak = [m for m in zewnetrzne if importlib.util.find_spec(m) is None]
sprawdz("wszystkie zewnetrzne moduly sa zainstalowane", not brak, brak)

wymagania = pathlib.Path("agent-v2/requirements.txt").read_text(encoding="utf-8").lower()
niezadeklarowane = [m for m in zewnetrzne
                    if m.lower() not in wymagania
                    and m.lower().replace("dotenv", "python-dotenv") not in wymagania]
sprawdz("wszystkie sa zadeklarowane w requirements.txt", not niezadeklarowane,
        niezadeklarowane)
sprawdz("trafilatura jest w wymaganiach (to on wywrocil pierwszy artykul)",
        "trafilatura" in wymagania)

print()
print("=== 2. ETAP fetch NAPRAWDE DZIALA ===")
try:
    import trafilatura
    tekst = trafilatura.extract(
        "<html><body><article><p>A rule nobody voted on.</p>"
        "<p>Second paragraph with substance.</p></article></body></html>",
        include_comments=False)
    sprawdz("trafilatura wyciaga tresc", bool(tekst) and "rule" in (tekst or ""), tekst)
except Exception as exc:
    sprawdz("trafilatura wyciaga tresc", False, "%s: %s" % (type(exc).__name__, exc))

print()
print("=== 3. NIE BIERZEMY TEMATU, KTORY JUZ WYSZEDL ===")
kat = pathlib.Path(tempfile.mkdtemp())
oryg_promocja = stages.PROMOCJA
try:
    stages.PROMOCJA = kat / "promocja.json"
    stages.PROMOCJA.write_text(json.dumps([
        {"url": "https://x/p/egg", "tytul": "Example Article Three",
         "tekst": "...", "wystawione": 2, "ostatnia": "2026-08-17"}
    ]), encoding="utf-8")
    conn = db.connect(kat / "t.db")
    katy = stages.recent_angles(conn)
    print("    katy podane skautowi: %s" % [k[:44] for k in katy[:4]])
    sprawdz("opublikowany artykul jest wsrod zakazanych katow",
            any("Example Article Three" in k for k in katy), katy[:3])

    stages.PROMOCJA.write_text("[]", encoding="utf-8")
    bez = stages.recent_angles(conn)
    sprawdz("bez listy promocji tego tematu NIE MA (test rozroznia)",
            not any("Example Article Three" in k for k in bez))

    stages.PROMOCJA = kat / "nie-ma.json"
    sprawdz("brak pliku promocji nie wywala", isinstance(stages.recent_angles(conn), list))
finally:
    stages.PROMOCJA = oryg_promocja

print()
print("=== 4. SCIEZKA ARTYKULU MA SWOJ LIMIT CZASU W USLUDZE ===")
usluga = pathlib.Path("agent-v2/systemd/nia-artykul.service").read_text(encoding="utf-8")
import re  # noqa: E402
m = re.search(r"TimeoutStartSec=(\d+)", usluga)
sprawdz("usluga artykulu ma limit czasu", bool(m))
if m:
    print("    limit: %s min" % (int(m.group(1)) // 60))
    sprawdz("limit co najmniej godzina", int(m.group(1)) >= 3600, m.group(1))

print()
print("=== WYNIK: %s zdanych, %s oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
