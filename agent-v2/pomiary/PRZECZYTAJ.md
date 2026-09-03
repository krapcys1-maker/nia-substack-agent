# Pomiary, nie testy

Skrypty w tym katalogu **nic nie sprawdzaja** — mierza rzeczywistosc i wypisuja
liczby do decyzji czlowieka. Nie maja asercji, nie zwracaja „zdane/oblane"
i nie naleza do zadnej petli.

Wydzielone, bo raz juz wrzucilem pomiar miedzy testy i petla policzyla go jako
porazke — tak samo, jak wczesniej wrzucilem miedzy testy skrypt, ktory
publikowal na zywym koncie. Rzecz, ktora coS ROBI albo coS MIERZY, nie jest
testem, choćby nazywala sie `test_`.

| plik | co mierzy | koszt |
|---|---|---|
| `korpus_fedreg.py` | ile ze stu przepisow Federal Register niesie spor | darmowe, ale kilka minut sieci |

## Wynik ostatniego pomiaru (2026-08-19)

Na sto najnowszych przepisow typu RULE:

- **20% niesie gesty spor** (>=5 sladow odpowiedzi na zastrzezenia)
- 12% slaby, 68% zaden — dwie trzecie to rutyna w rodzaju procedur podejscia
- gesty dokument ma srednio **91 587 znakow** wobec 37 342 przecietnego

Wniosek: zeby dostac dziesiec gestych preambul, trzeba przejrzec okolo
piecdziesieciu przepisow. Filtr jest darmowy, wiec model dostaje wylacznie to,
co ma szanse przejsc bramki.
