#!/usr/bin/env bash
# Wdrozenie nowej wersji z siecia bezpieczenstwa.
#
# Dotad wgrywalismy kod przez zwykly `git pull`. Jesli nowa wersja jest zepsuta,
# agent po prostu przestaje dzialac, a dowiadujemy sie o tym dopiero z kontroli
# ciszy — czyli po dobie milczenia na koncie.
#
# Tu jest odwrotnie: najpierw sprawdzamy, czy nowa wersja W OGOLE WSTAJE, i jesli
# nie, wracamy do poprzedniej, zanim ktokolwiek zauwazy.
set -euo pipefail

cd "$(dirname "$0")/.."

# TEN SKRYPT DZIALA TYLKO NA SERWERZE. Ciagnie z origin, uzywa .venv/bin/python
# i pyta o zamek przebiegu — wszystkie trzy rzeczy maja sens wylacznie tam.
#
# Uruchomiony z maszyny roboczej nie mowil tego wprost, tylko brnal dalej i
# konczyl mylnym komunikatem. 30 sierpnia wypisal „PRZEBIEG TRWA (zamek zajety)"
# w chwili, gdy na serwerze nie chodzil zaden proces, a usluga byla wygaszona.
# Przyczyna: sprawdzal zamek LOKALNY, ktory zostal po nieumyslnym przebiegu na
# maszynie roboczej, a Git Bash nie ma polecenia `flock`, wiec „nie umiem
# sprawdzic" wychodzilo z tego samego warunku co „zajete". Pol godziny na
# szukanie procesu, ktorego nie bylo.
if [ ! -x ".venv/bin/python" ]; then
    echo "  TO NIE JEST SERWER — brak .venv/bin/python."
    echo "  Wdrazaj tak:  ssh <serwer> 'cd ~/nia-substack-bot && bash agent-v2/wdroz.sh'"
    exit 2
fi
if ! command -v flock >/dev/null 2>&1; then
    echo "  BRAK POLECENIA flock — nie umiem sprawdzic, czy trwa przebieg."
    echo "  Przerywam, bo wdrozenie w srodku przebiegu podmienia kod pod dzialajacym procesem."
    exit 2
fi

POPRZEDNIA=$(git rev-parse --short HEAD)
echo "  wersja przed wdrozeniem: $POPRZEDNIA"

# Nie wdrazamy w srodku przebiegu. Pytamy o to sam zamek, ktory przebieg trzyma
# — a nie o liste procesow, bo `pgrep -f` potrafi dopasowac WLASNE polecenie,
# jesli wzorzec wystapi w jego wierszu (stad nawiasy: "[r]un" nie pasuje do
# samego siebie). Zamek jest zrodlem prawdy, pgrep tylko zapasem, gdy zamka
# jeszcze nie ma.
ZAMEK="agent-v2/data/agent.lock"
if [ -e "$ZAMEK" ] && ! flock -n "$ZAMEK" -c true 2>/dev/null; then
    echo "  PRZEBIEG TRWA (zamek zajety) — nie wdrazam, sprobuj po jego zakonczeniu"
    exit 1
fi
# TYLKO PROCESY PYTHONA. Wzorzec bez `python` lapal takze cudze POLECENIA, w
# ktorych ten napis wystepuje — a wystarczy jedna petla czekajaca
#     while pgrep -f "run.py --dzien"; do sleep 60; done
# zeby zablokowac wdrozenia na zawsze: jej wlasny wiersz polecenia zawiera
# wzorzec, wiec czeka sama na siebie i nigdy nie konczy. Dwie takie sieroty
# wisialy na serwerze 30 sierpnia i przez pol godziny udawaly trwajacy przebieg.
#
# Nawiasy w "[r]un" zostaja — chronia przed dopasowaniem samego `pgrep`.
if pgrep -f "python.*[r]un\.py --dzien" >/dev/null; then
    echo "  PRZEBIEG TRWA — nie wdrazam, sprobuj po jego zakonczeniu"
    exit 1
fi

git fetch -q origin
NOWA=$(git rev-parse --short origin/main)
if [ "$POPRZEDNIA" = "$NOWA" ]; then
    echo "  nic nowego, wersja $NOWA juz jest"
    exit 0
fi
echo "  wciagam wersje: $NOWA"
git merge -q --ff-only origin/main

# --- SPRAWDZENIE, czy nowa wersja wstaje ------------------------------------
echo "  sprawdzam nowa wersje..."
if ! AGENT_V2_SERVER=1 .venv/bin/python -c "
import sys
sys.path.insert(0, 'agent-v2')
import config, db, llm, stages, browser, kanal, alarm, gates, style, run
assert config.MODEL_FOR and config.PRICING, 'pusta konfiguracja'
assert callable(browser.wystaw_notke) and callable(stages.notki_dnia)
assert config.OKNO_PUBLIKACJI_ET, 'brak okna publikacji'
print('  moduly wstaja i konfiguracja jest kompletna')
"; then
    echo "  NOWA WERSJA NIE WSTAJE — wracam do $POPRZEDNIA"
    git reset -q --hard "$POPRZEDNIA"
    exit 1
fi

# --- SPRAWDZENIE, czy sesja i konto nadal dzialaja --------------------------
if ! AGENT_V2_SERVER=1 timeout 180 .venv/bin/python -c "
import sys
sys.path.insert(0, 'agent-v2')
import browser
p, br, ctx = browser.podlacz_sie()
page = ctx.new_page()
try:
    assert browser.wlasciwe_konto(page), 'nie to konto albo brak sesji'
    print('  sesja i konto potwierdzone')
finally:
    page.close(); br.close(); p.stop()
"; then
    echo "  NOWA WERSJA NIE DOGADUJE SIE Z SUBSTACKIEM — wracam do $POPRZEDNIA"
    git reset -q --hard "$POPRZEDNIA"
    exit 1
fi

sudo cp agent-v2/systemd/*.service agent-v2/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
echo "  WDROZONE: $POPRZEDNIA -> $NOWA"
echo "  cofniecie jednym poleceniem:  git reset --hard $POPRZEDNIA"
