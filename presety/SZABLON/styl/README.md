# styl/ — glos tego kartridza

- `profil_pozytywny.md` — do czego dazy pisarz artykulu.
- `profil_negatywny.md` — czego nie wolno w artykulach i notkach.
- `korpus.txt` (opcjonalnie) — teksty, ktorych glos ma nasladowac pisarz:
  TWOJE wlasne albo takie, do ktorych masz prawo (domena publiczna, CC BY,
  OGL). Nigdy cudza publicystyka bez licencji. Akapity oddzielone pusta
  linia. Po dodaniu wskaz plik w `preset.toml` (`styl.korpus = "styl/korpus.txt"`)
  i przypnij: `python narzedzia/przypnij_styl.py --korpus presety/<nazwa>/styl/korpus.txt --pokaz`.
  Gdy korpus idzie do gita, obok musi lezec `KORPUS_ZRODLA.md` z atrybucja
  kazdego zrodla i jego licencja — wzor w `presety/ai/styl/`.

Obie sciezki profili w `preset.toml` sa wzgledem katalogu presetu.
