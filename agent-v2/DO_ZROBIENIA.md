# Rzeczy do zrobienia

Jedno miejsce, żeby nie były rozsypane po trzech. Uszeregowane **wagą**, nie
kolejnością znalezienia. Pozycja znika stąd, gdy jest zamknięta i sprawdzona
na produkcji — nie wtedy, gdy przechodzi test.

**Czego ta lista NIE zawiera** — żeby nie powstała czwarta kopia tych samych
zapisów, bo to w tym repozytorium osobna klasa błędu:

- otwarte długi doktryny → `agent-v2/DOKTRYNA.md`, sekcja „Rozbieżności doktryny z kodem"
- pełny audyt modelu spoza projektu → `docs/ROZSTRZYGNIECIE_2026-09-02.md`
- pamięć / warstwa oszacowań → gałąź `pamiec/oszacowania`, niewdrożona

Stan na 2 września 2026, wieczór. Produkcja na `5684d12`.

---

## ~~1. Bank może zniknąć bez śladu i raz już zniknął~~ — **ZAMKNIĘTE**

`_zapisz_indeks` to nieatomowy `write_text` (`stages.py`), a `wczytaj_indeks`
traktuje nieczytelny plik jak **pusty**. Przebieg ubity w trakcie zapisu kasuje
więc cały bank po cichu: nie ma wyjątku, nie ma linii w logu, jest pusta pula.

**To nie jest teoria.** Najstarszy ocalały wpis w indeksie pochodzi z 30 sierpnia
12:44:37. Wcześniejsza kohorta — bank rósł 66 → 119 wolnych pozycji między 25
a 29 sierpnia, opłacony 22 wywołaniami za **1,51 USD** — zniknęła w całości, bez
ani jednego wpisu `uzyty` i bez ani jednego `przeterminowany`. Drugie możliwe
wyjaśnienie to świadomy reset podczas testów tamtego dnia; ze śladów nie da się
rozstrzygnąć, które zaszło, i to samo w sobie jest wadą.

**Zrobione, gdy:** zapis idzie przez plik tymczasowy i `os.replace` (atomowo),
a nieczytelny plik **oblewa głośno** zamiast udawać pusty bank. Do tego jedna
kopia zapasowa obok, jak przy `promocja.json`.

**ZAMKNIĘTE — sprawdzone uruchomieniem, nie odczytane ze źródła.** Ta pozycja
stała tu jako otwarta, a poprawka była już w kodzie: dokument jest z 2 września,
kod jest nowszy. To sama w sobie drobna wada tej listy — pozycja miała zniknąć
przy zamknięciu.

Stan faktyczny:

* `stages._zapisz_indeks` pisze do `indeks_kandydatow.json.nowy` i podmienia
  przez `os.replace`, czyli atomowo. Nie ma już szczeliny, w której plik jest
  obcięty.
* `stages.wczytaj_indeks` **odkłada uszkodzony plik obok** jako
  `.json.uszkodzony-<znacznik>` i zgłasza to głośno:

  ```
  [indeks] UWAGA: plik banku jest USZKODZONY, nie pusty.
  Odlozony jako indeks_kandydatow.json.uszkodzony-20260903-161127
  — material trzeba odzyskac recznie.
  ```

  Przebieg idzie dalej, bo doktryna mówi, że nic nie ma zatrzymywać treści.
* Pilnują tego dwa zestawy: `tests/test_indeks_kandydatow.py` (54 sprawdzenia)
  i `tests/test_kotwica_przezywa_zapis.py` (12). Oba przechodzą.

Czego **nadal nie ma**: drugiej kopii zapasowej obok, jak przy `promocja.json`.
Przy zapisie atomowym i głośnym zgłaszaniu jej wartość jest mniejsza, ale nie
zerowa — plik odłożony jako uszkodzony trzeba odzyskać ręcznie.

---

## 2. Znacznik kanału obejmuje 3 miejsca z 26

Kolumna `akcja` w `calls` działa (potwierdzone niezależnie na produkcji: zapisuje
się, nie przecieka, wytrzymuje wyjątek, dekorator obejmuje generatory). Ale
wpięta jest tylko w dwóch wywołaniach `comment_on` i w `notki_dnia`.

Zmierzone na 7 dniach: **8,84 z 16,97 USD (52,1%) nie dostanie kanału nigdy** —
w tym `write` (4,11 USD, cały artykuł), `discovery` (1,82), `cele`, `synthesis`,
`scout`, `reply`, `review`, `forma`, `classify`, `obraz`, `grafika`, `restack`,
`warto_pisac`, `wybor`, `feasibility`, `bibliotekarz`, `fedreg`.

Dopóki to stoi, miara „różni ludzie na dolara" nie istnieje dla artykułów,
tematów ani odpowiedzi — czyli dla ponad połowy rachunku.

**Zrobione, gdy:** każde płatne wywołanie jest osiągalne wyłącznie ze ścieżki
z kanałem, a test liczący to z drzewa składni **oblewa**, gdy ktoś doda nowe
wywołanie bez kanału.

---

## 3. Dwa bloki niezależnie zużywają ten sam budżet komentarzy

Blok pod artykułami bierze `na_teraz["komentarze"]` celów, a późniejszy blok
dyskusji pod notkami bierze **jeszcze** `max(1, na_teraz["komentarze"] // 2)`.
Oba podbijają ten sam licznik, między nimi nie ma odjęcia. Przy przydziale N
jeden przebieg może zrobić do `N + N/2` publikacji.

Z audytu GPT (G1), niezweryfikowane pomiarem — do sprawdzenia przed poprawką,
bo dziś wolumeny są **poniżej** normy, a nie powyżej, więc może to nie boli.

---

## 4. Po nieudanym przebiegu norma nie jest domykana

Docstring obiecuje, że przerwany przebieg się nie liczy i ostatni dzieli przez
jeden. Kod odejmuje od stałej 5 tylko liczbę statusów `DONE`, więc przy jednej
wcześniejszej porażce przed ostatnim terminem dzieli resztę pracy przez dwa
i zostawia połowę niewykonaną.

Z audytu GPT (G3), niezweryfikowane pomiarem.

---

## 5. Ostatni przebieg może wpaść w następną dobę UTC

Termin 23:40 plus `RandomizedDelaySec=1500` sięga 00:05. Budżet i licznik biorą
dzień z `datetime.now(timezone.utc)`, nie z terminu zegara — więc doba może mieć
cztery, pięć albo sześć uruchomień, a rozdzielnik zakłada stałe pięć.

Z audytu GPT (G4), niezweryfikowane pomiarem.

---

## 6. Czternaście publikacji w tydzień bez potwierdzenia

Osiem komentarzy i sześć odpowiedzi z powodem „Substack nie potwierdził, że
wyszło" (7 dni do 2 września). Przy 57 komentarzach to 14% strat, i **nie
wiadomo, czy tekst wisi, czy przepadł** — potwierdzanie po API oddaje wtedy
pustkę, a my zapisujemy porażkę.

**Zrobione, gdy:** przy braku potwierdzenia jest druga próba odczytu po
odstępie, a jeśli i ona milczy, wpis dostaje status „niepewne" zamiast
„nieudane" — żeby licznik strat nie mieszał dwóch różnych rzeczy.

---

## 7. Wolumeny poniżej normy — obserwacje na 33%

Zmierzone przez alarm na 7 dniach: obserwacje **0,14/dzień wobec ~0,4** (33%),
notki 2,86 wobec 5 (67%), komentarze 8,14 wobec ~19 (70%), polubienia 81%,
restacki 88%. Subskrypcje jako jedyne powyżej (200%).

Alarm nazywa to wprost: „to jest ta awaria, której nie widać w logu". Nic się
nie wywala — po prostu wychodzi mniej, niż doktryna deklaruje. Przyczyna
niezbadana.

---

## 8. Trzy dziury w pomiarze, przez które nie da się liczyć skutku

- **`nasz_id` przy odpowiedziach: 0 z 56** w całej historii. Kanał odpowiedzi
  jest niemierzalny w obie strony — nie wiadomo, co dostało reakcję.
- **`komu` przy komentarzach: nie istnieje nigdy** (0 z 129). Jest tylko
  `publikacja`. Przy polubieniach `komu` ma 21 z 179.
- **`uchwyty` przy skutkach: 22 z 221**, i wszystkie z jednego dnia. Dopisanie
  wstecz jest niemożliwe (`dopisz_skutki` pomija zdarzenia już zapisane).

Bez pierwszych dwóch nie policzy się, który komentarz co przyniósł. Trzecia
zamyka się sama z czasem, ale dopiero od 1 września.

---

## 9. Test podłóg na serwerze mierzy co innego niż lokalnie

`test_podlogi_playbook.py` szuka prawdziwego artykułu 0025 w `data/articles/`.
Katalog jest w `.gitignore`, więc **na świeżym klonie i na serwerze pliku nie
ma** — a wtedy test po cichu podstawia wbudowane wycinki i dalej drukuje same OK.

Docstring mówi: „każda nowa podłoga MUSI się na nim zapalić". Fallback tego
zakazu nie egzekwuje.

**Zrobione, gdy:** albo wycinki 0025 wchodzą do repozytorium jako materiał
dowodowy, albo brak pliku **oblewa** test.

---

## 10. Cztery pliki omijają prawdziwy `parse_json`

Podmieniają nie tylko `llm.call`, ale też `llm.parse_json` na lambdę ignorującą
`raw` — czyli omijają jedyną funkcję tłumaczącą odpowiedź modelu na kształt
oczekiwany przez kod (30 linii obsługi prozy wokół JSON-a, której własny
docstring podaje koszt awarii: „dwadzieścia wyszukiwań i 0,13 USD, po czym
oddało zero").

`test_cel_i_tik_w_prompcie.py`, `test_wybor_odpowiedzi.py`,
`test_podlogi_z_pamieci.py`.

**Zrobione, gdy:** podmieniają tylko `call` i oddają `json.dumps({...})` — wzorzec
już działa w `test_bramka_banku.py` i `test_pas_wydarzen.py`.

---

## 11. Dziewięć asercji pilnuje napisów w źródle, nie zachowania

Każda przeżyje przeniesienie zachowania do martwej gałęzi i każda oblewa przy
kosmetycznym refaktorze:

| plik:linia | co pilnuje |
|---|---|
| `test_martwe_sygnaly.py:265` | `"pora_na_publikacje()" in reszta` — **etykieta mówi „REALNIE WOŁANE", warunek to grep** |
| `test_martwe_sygnaly.py:326` | `"_stale_sygnaly(topics" in st_src` — to samo |
| `test_pole_komentarza.py:217` | `"pole.click(timeout=8_000)"` — `8000` zamiast `8_000` oblewa bez zmiany zachowania |
| `test_stawka.py:308` | cała linia `stages.py:5337` |
| `test_czas.py:73` | `"_KONIEC_CZASU = time.time() + max("` |
| `test_glebokosc.py:88` | `"stages.write(conn, run_id, card, glebokosc)"` |
| `test_indeks_kandydatow.py:159` | `"dopisz_kandydatow(fakty)"` |
| `test_kotwica_w_kanalach.py:131` | „ale NIE kasujemy tematów" — spełnione przez **docstring innej funkcji**; `grep -ic "nie kasujemy"` = 0 |
| `test_kotwica_w_kanalach.py:123` | „skaut liczy udział z kanałów" — trafia w `print` z **etapu ciekawostek**, nie ze skauta |

**Zrobione, gdy:** pytają o drzewo składni (jak `test_waga_artykulu.py`) albo
uruchamiają z atrapą i liczą wywołania (jak `test_regula_naprawy.py`).

---

## 12. Drobne, ale zawyżają licznik zdanych

- `test_pobieranie.py:95` i `test_jednostki_systemd.py:57` — `sprawdz(nazwa, True)`
  poza blokiem `except`. **Nie mogą oblać nigdy.**
- `test_komentarz_potwierdzony.py:544-558` — sekcja 9 przybita do `index()`
  z 16 spacjami wcięcia wpisanymi w asercję. Sekcje 1–8 są mocne; skasować samą 9.
- `test_slad_przebiegu.py:131` — okno 2600 znaków od `def rytm(`, kończące się
  w połowie funkcji. Działa przypadkiem.
- `test_pisarz_zakazy.py:116` — sprawdza istnienie **komentarza** w `config.py`.
  Test dokumentacji podszyty pod test kodu; zostawić, ale nazwać wprost.
- `test_bank_notek.py:5` i `test_indeks_kandydatow.py:19` przestawiają
  `config.DATA_DIR` globalnie i nie cofają. Przywracać w `finally`.

---

## 13. Czternaście testów celuje w produkcyjną bazę

`config.py:31-32` liczy `DB_PATH` z `DATA_DIR` **przy imporcie**. Test, który
podmienia `config.DATA_DIR` na katalog tymczasowy, nie zmienia przez to
`DB_PATH` — ta nadal wskazuje produkcyjną bazę.

Policzone: **23 pliki testowe przestawiają `DATA_DIR`, tylko 9 przestawia też
`DB_PATH`.** Dziś nic z tego nie strzela, bo te akurat testy nie otwierają
połączenia — ale przebieg sięgający `db.connect()` przy takim stanie **dopisał
kolumny do produkcyjnej bazy** (sprawdzone w piaskownicy).

To ta sama klasa błędu, co zatrucie `tematy_przegrane.json` 2 września (294 z
400 wpisów było atrapami z testów), tylko innym wejściem. Tamto zamknięto
stałą `config.W_TESCIE`; tu potrzebne jest zamknięcie **na poziomie klasy** —
jedna droga przestawiająca komplet ścieżek pochodnych plus głośna odmowa
otwarcia produkcyjnej bazy w trybie testowym.

---

## 14. Notatka `co_dodamy` zjada tekst źródłowy przy długich wpisach

`comment_on` przycina `post["text"][:9000]` przed doklejeniem notatki, a całe
`body` jest dopiero potem cięte na `[:12000]`. Zmierzone na prawdziwym artykule
13 269 znaków: prompt z notatką ma 18 902 znaki, bez notatki 21 412 — czyli
model widzi **o ~3000 znaków mniej samego artykułu** w zamian za ~490 znaków
notatki. Przy wpisach poniżej 9000 znaków (wszystkie notki, większość postów)
straty nie ma.

**Uśpiona pułapka obok:** gdyby ktoś kiedyś podał `fakty=` do `comment_on`,
drugie `[:9000]` w bloku `co_dodamy` **skasowałoby właśnie doklejony blok
VERIFIED FACTS**. Dziś żaden wołający `fakty` nie podaje, więc jest to
nieosiągalne — ale gałąź `co_dodamy` właśnie ożyła, więc pułapka jest jeden
argument od zadziałania.

Do tego docstring `comment_on` nadal mówi „Milczenie jest pełnoprawną
odpowiedzią i nie jest porażką", co po zmianie promptu przestanie być prawdą.

---

## 14. `Callable` w adnotacji bez importu

`oszacowania.py:176` (gałąź `pamiec/oszacowania`) używa `Callable`, a moduł
importuje z `typing` tylko `Any`. Program działa dzięki `from __future__ import
annotations`, ale `typing.get_type_hints` na tej funkcji rzuci `NameError`,
a każdy linter to zgłosi.

---

## Czeka na decyzję właściciela — nie na kod

Z audytu GPT (G5) i z dzisiejszego rozstrzygnięcia. **Nie są to usterki, dopóki
właściciel nie powie, że są:**

- artykuł planowany **co tydzień**, nie co miesiąc
- komentarze **15–23**, a przez pierwsze 30 dni efektywnie 15–19, przy celu 20–30
- **ciche dni zerują notki**, więc „pięć notek dziennie" nie jest kontraktem na
  każdą dobę
- czy **artykuł ma nadal mieć pierwszeństwo**, skoro zdanie „subskrypcje
  przynoszą artykuły" upadło pomiarem, a panel Substacka przypisuje 5 z 6
  zapisów **notkom**

---

## Zasada, która z tego wynika

Większość pozycji 9–12 to jedna wada w wielu przebraniach: **asercja po treści
źródła zamiast po zachowaniu**. Pilnuje kształtu kodu, nie tego, co kod robi —
więc przeżywa przeniesienie zachowania do martwej gałęzi i umiera przy zmianie
wcięcia.

Gdy wybór stoi między „grep w źródle" a niczym, lepszy jest **AST** albo
**uruchomienie z atrapą i policzenie wywołań**.

A gdy poprawka jest wdrożona — dowodem jest **ślad z produkcji**, nie zielony
zestaw testów. Także ten na serwerze.
