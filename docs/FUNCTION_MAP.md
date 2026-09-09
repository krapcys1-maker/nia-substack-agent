# Function map — every function in the bot

**Generated** by `python narzedzia/mapa_funkcji.py`. Do not edit by hand.
Built from the modules' **syntax tree**, not from grepping for strings.

Scope: `agent-v2/*.py` only — what the systemd timers actually run.

The **what it does** column comes from each function's own docstring, so it is in Polish: that is the language of this codebase, and the README says so. Everything this generator writes itself is in English.

## Counts

| what | how many |
|---|---|
| modules | 37 |
| functions and methods | 772 |
| functions that call a paid model | 27 |
| functions that touch the browser | 67 |
| functions that touch the database | 49 |

## Legend

| marker | means |
|---|---|
| **$**(stage) | calls a paid model; the bracket holds the `purpose` the cost is booked under in the `calls` table |
| WWW | touches the browser (`page.*`, `context.*`, `browser.*`) — the Substack layer |
| DB | reads or writes the database |
| DEAD? | no call edge in `agent-v2/*.py` points at it |

`DEAD?` is a **suspicion, not a verdict**. A call through a variable,
`getattr`, a dispatch table or `functools.partial` leaves no edge, and
`main()` plus the systemd entry points have no callers by definition.
For paid calls the verdict comes from
`agent-v2/tests/test_kanal_platnego_wywolania.py`.

## Modules

| module | functions | paid | WWW | DB | what it is for |
|---|---|---|---|---|---|
| [`aktualne_modele.py`](#agent-v2aktualne-modele-py) | 4 | 1 | 0 | 0 | Co w tej dziedzinie jest AKTUALNE dzisiaj — pytane na zywo, nie z pamieci. |
| [`alarm.py`](#agent-v2alarm-py) | 29 | 0 | 1 | 6 | Alarm do właściciela i kontrola zdrowia agenta. |
| [`artykul_z_puli.py`](#agent-v2artykul-z-puli-py) | 18 | 1 | 1 | 2 | Artykul bierze temat z tej samej puli, co notki. |
| [`audyt_kosztow.py`](#agent-v2audyt-kosztow-py) | 4 | 0 | 0 | 1 | Read-only audit of the API ledger, research sources and editorial memory. |
| [`audyt_researchu.py`](#agent-v2audyt-researchu-py) | 3 | 0 | 0 | 0 | Audyt segmentu researchu na ZYWYCH danych, jednym poleceniem. |
| [`audyt_systemu.py`](#agent-v2audyt-systemu-py) | 9 | 0 | 1 | 0 | Audyt CALEGO systemu na zywych danych, jednym poleceniem. |
| [`audyt_tematow.py`](#agent-v2audyt-tematow-py) | 4 | 0 | 0 | 0 | Audyt segmentu tematow — kazdy etap na ZYWYCH danych, jednym poleceniem. |
| [`bramki.py`](#agent-v2bramki-py) | 9 | 0 | 0 | 0 | Co moze zatrzymac tresc — wyliczone z kodu, nie spisane z pamieci. |
| [`browser.py`](#agent-v2browser-py) | 105 | 0 | 47 | 0 | Czytanie stron przeglądarką — tam, gdzie zwykły HTTP nie wystarcza. |
| [`browser_reader.py`](#agent-v2browser-reader-py) | 5 | 0 | 1 | 0 | Bound source reads, including Playwright shutdown, in an owned subprocess. |
| [`call_runtime.py`](#agent-v2call-runtime-py) | 10 | 0 | 1 | 0 | Per-operation deadlines and usage; workers never write to the database. |
| [`config.py`](#agent-v2config-py) | 44 | 0 | 0 | 0 | Jedyne miejsce ze stałymi. |
| [`db.py`](#agent-v2db-py) | 15 | 0 | 0 | 10 | Baza: cztery tabele, waskie migracje kolumn, zero triggerow i limitow CHECK. |
| [`feed_cache.py`](#agent-v2feed-cache-py) | 2 | 0 | 0 | 0 | Per-instance, per-URL feed recovery. |
| [`gates.py`](#agent-v2gates-py) | 22 | 0 | 0 | 0 | Bramki wykrywaja naruszenia, ale zadna nie blokuje artykulu. |
| [`insights.py`](#agent-v2insights-py) | 12 | 0 | 0 | 1 | Read-only cost, outcome and research report. |
| [`interaction_history.py`](#agent-v2interaction-history-py) | 3 | 0 | 0 | 0 | Skip confirmed interactions before paying to write them again. |
| [`jezyki.py`](#agent-v2jezyki-py) | 5 | 0 | 0 | 0 | Wzorce bramek ZALEZNE OD JEZYKA — i glosny sprzeciw, gdy jezyka nie ma. |
| [`kanal.py`](#agent-v2kanal-py) | 13 | 0 | 3 | 0 | Kanal czytelnika — jedyne zrodlo celow do komentowania. |
| [`konfiguracja.py`](#agent-v2konfiguracja-py) | 45 | 0 | 0 | 0 | Wczytanie `konfiguracja.toml` i pol presetu — jeden kontrakt pol, jeden zapis. |
| [`kopia_subskrybentow.py`](#agent-v2kopia-subskrybentow-py) | 4 | 0 | 1 | 0 | Kopia listy subskrybentow — jedyne aktywo, ktorego nie da sie odtworzyc. |
| [`korpus_kanalow.py`](#agent-v2korpus-kanalow-py) | 14 | 0 | 0 | 0 | Tematy z kanalow, ktore robia dokladnie to, co ma robic nasza publikacja. |
| [`llm.py`](#agent-v2llm-py) | 26 | 0 | 0 | 4 | Provider calls with per-attempt accounting, reservations and deadlines. |
| [`migracja_okno_promocji.py`](#agent-v2migracja-okno-promocji-py) | 2 | 0 | 0 | 0 | Jednorazowe uzupelnienie pola `dodane` w kolejce promocji. |
| [`norma.py`](#agent-v2norma-py) | 16 | 0 | 0 | 1 | Ile agent naprawde zrobil, dzien po dniu, wobec normy. |
| [`personality.py`](#agent-v2personality-py) | 23 | 1 | 0 | 0 | Opt-in conversational short forms. |
| [`preset.py`](#agent-v2preset-py) | 40 | 0 | 0 | 0 | Preset: kartridz z CALA redakcja, podlaczany i odlaczany jednym poleceniem. |
| [`raport_statystyk.py`](#agent-v2raport-statystyk-py) | 5 | 0 | 0 | 0 | Co przyniosla kazda notka, restack i artykul — do czytania przez czlowieka. |
| [`research_tasks.py`](#agent-v2research-tasks-py) | 3 | 0 | 0 | 0 | Record article evidence gaps and target an existing second search at them. |
| [`result_cache.py`](#agent-v2result-cache-py) | 5 | 0 | 0 | 0 | Content-addressed cache. |
| [`retry_policy.py`](#agent-v2retry-policy-py) | 4 | 0 | 0 | 0 | Remember server-requested pauses without treating a deferred call as an attempt. |
| [`run.py`](#agent-v2run-py) | 41 | 0 | 10 | 4 | Jedno polecenie uruchamiające — to samo lokalnie i na serwerze. |
| [`stages.py`](#agent-v2stages-py) | 176 | 24 | 1 | 20 | Etapy lancucha, po kolei, w pamieci. |
| [`statystyki.py`](#agent-v2statystyki-py) | 11 | 0 | 0 | 0 | Statystyki wystawionych pozycji: kto to zobaczyl i co z tego wyniklo. |
| [`style.py`](#agent-v2style-py) | 9 | 0 | 0 | 0 | Głos redakcyjny: korpus próbek i dwa profile stylu. |
| [`tekst_strony.py`](#agent-v2tekst-strony-py) | 5 | 0 | 0 | 0 | Read explicitly marked article bodies before generic page extraction. |
| [`wzajemnosc.py`](#agent-v2wzajemnosc-py) | 27 | 0 | 0 | 0 | Czy zaczepieni odwzajemniaja sie, i skad naprawde biora sie czytelnicy. |

---

<a id="agent-v2aktualne-modele-py"></a>
## `agent-v2/aktualne_modele.py`

Co w tej dziedzinie jest AKTUALNE dzisiaj — pytane na zywo, nie z pamieci.

4 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 95 | `_swieze(dane)` | — | Czy zapisana odpowiedz jest jeszcze wazna. | `aktualne_modele.jako_tekst`, `aktualne_modele.pobierz` |
| 109 | `wczytaj()` | — | Ostatnia zapisana odpowiedz NA TO SAMO PYTANIE. | `aktualne_modele.jako_tekst`, `aktualne_modele.pobierz` |
| 134 | `pobierz(conn, run_id, wymus)` | **$**(aktualne_modele) | Aktualny stan modeli. | `aktualne_modele (poziom modulu)`, `stages.znajdz_ciekawostki` |
| 203 | `jako_tekst(dane)` | — | Stan modeli w postaci, ktora wchodzi do promptu. | `aktualne_modele (poziom modulu)`, `stages.znajdz_ciekawostki` |

---

<a id="agent-v2alarm-py"></a>
## `agent-v2/alarm.py`

Alarm do właściciela i kontrola zdrowia agenta.

**Wejscie produkcyjne:** `nia-alarm.timer`, raz na dobe 07:00 UTC: `alarm.py`

29 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 36 | `_ustawienia()` | — | — | `alarm.skonfigurowany`, `alarm.wyslij` |
| 49 | `skonfigurowany()` | — | — | `alarm (poziom modulu)`, `alarm.wyslij` |
| 54 | `_ostatnio(klucz)` | — | — | `alarm.wyslij` |
| 64 | `_zapisz(klucz)` | — | — | `alarm.wyslij` |
| 77 | `wyslij(klucz, temat, tresc)` | — | Wysyła alarm. | `alarm (poziom modulu)`, `alarm.sprawdz_przebiegi_i_ostrzez`, `alarm.sprawdz_sesje_i_ostrzez`, `alarm.sprawdz_wszystko` *(+2)* |
| 122 | `brak_presetu()` | — | Silnik bez podlaczonego presetu ODMAWIA startu z zegara — to ma byc alarm, nie cisza. | `alarm.sprawdz_wszystko` |
| 139 | `konto_placeholder()` | — | Konto instalacji nadal jest placeholderem — bot sprawdzalby profil „your-handle". | `alarm.sprawdz_wszystko` |
| 162 | `artykul_zalegly()` | — | Czy gotowy artykul lezy na dysku niewystawiony dluzej niz dobe. | `alarm.sprawdz_wszystko` |
| 187 | `sprawdz_sesje_i_ostrzez()` | WWW | Pilnuje jedynej rzeczy, która zatrzymuje agenta bez żadnego błędu. | `alarm (poziom modulu)`, `run.dzien` |
| 208 | `sprawdz_przebiegi_i_ostrzez(ile)` | DB | Alarmuje, gdy agent pada raz za razem. | `alarm (poziom modulu)` |
| 279 | `max_dzialan_dziennie()` | — | Ile dzialan na dobe uznajemy jeszcze za normalne. | `alarm.nadaktywnosc` |
| 290 | `_polaczenie()` | DB | — | `alarm.cisza`, `alarm.koszt`, `alarm.przeglad`, `alarm.zawieszone` |
| 296 | `cisza()` | DB | Czy agent w ogole cos ostatnio zrobil. | `alarm.sprawdz_wszystko` |
| 323 | `zawieszone()` | DB | Przebiegi, ktore zostaly w stanie RUNNING na zawsze. | `alarm.sprawdz_wszystko` |
| 342 | `dysk()` | — | — | `alarm.sprawdz_wszystko` |
| 353 | `_chwila_wpisu(tekst)` | — | Znacznik czasu wpisu dziennika jako moment w UTC, albo None. | `alarm.nadaktywnosc` |
| 374 | `nadaktywnosc()` | — | Czy agent nie zapetlil sie i nie zasypuje Substacka. | `alarm.sprawdz_wszystko` |
| 431 | `koszt()` | DB | Czy zblizamy sie do sufitu — dziennego ALBO miesiecznego. | `alarm.przeglad`, `alarm.sprawdz_wszystko` |
| 488 | `wolumeny()` | — | Czy agent robi tyle, ile deklaruje — czy tylko wyglada, ze robi. | `alarm.sprawdz_wszystko` |
| 525 | `powtorki()` | — | Czy agent nie zaczal pisac wciaz tego samego. | `alarm.sprawdz_wszystko` |
| 544 | `kopia_subskrybentow()` | — | Czy istnieje AKTUALNA kopia listy subskrybentow. | `alarm.sprawdz_wszystko` |
| 593 | `pomiar_wzajemnosci()` | — | Czy nadal mamy z czego liczyc, kto sie odwzajemnia. | `alarm.sprawdz_wszystko` |
| 617 | `wydarzenie_bez_pokrycia()` | — | Wydarzenie odhaczone jako obsluzone, a w tresci ani slowa o nim. | `alarm.sprawdz_wszystko` |
| 644 | `wydarzenie_bez_pokrycia._kiedy(wpis)` | — | — | `alarm.wydarzenie_bez_pokrycia` |
| 700 | `bank_bez_tematow()` | — | Czy w banku zostalo dosc ROZNYCH tematow na dzisiejsze notki. | `alarm.sprawdz_wszystko` |
| 748 | `sprawdz_wszystko()` | — | Uruchamia komplet kontroli i alarmuje o tym, co znalazl. | `alarm (poziom modulu)` |
| 835 | `przeglad(dni)` | DB | Co agent NAPRAWDE zrobil przez ostatnie dni i gdzie sie pomylil. | `alarm (poziom modulu)` |
| 932 | `_co_z_tego_wyszlo(wpisy)` | — | Czy nasze dzialania w ogole wracaja — i ktore z nich. | `alarm.przeglad` |
| 970 | `_co_z_tego_wyszlo._ilu(warunek)` | — | — | `alarm._co_z_tego_wyszlo` |

---

<a id="agent-v2artykul-z-puli-py"></a>
## `agent-v2/artykul_z_puli.py`

Artykul bierze temat z tej samej puli, co notki.

**Wejscie produkcyjne:** `nia-artykul.timer`, wtorek 14:00 UTC: `artykul_z_puli.py --wyslij`

18 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 121 | `temat_z_faktu(conn, run_id, fakt)` | **$**(wybor) | Zamienia udokumentowany fakt w brief artykulu. | `artykul_z_puli._przebieg` |
| 159 | `glebokosc_z_oceny(ocena)` | — | RICH / SINGLE / THIN — liczone z tego, co `warto_pisac` ZOBACZYLO. | `artykul_z_puli._napisz_i_zapisz` |
| 197 | `glebokosc_z_oceny._surowy(pole)` | — | — | `artykul_z_puli.glebokosc_z_oceny`, `artykul_z_puli.glebokosc_z_oceny._filar` |
| 205 | `glebokosc_z_oceny._filar(pole)` | — | — | `artykul_z_puli.glebokosc_z_oceny` |
| 221 | `uniesie_artykul(brief)` | — | Czy z tego faktu da sie napisac TYSIAC SLOW, czy tylko dwa zdania. | `artykul_z_puli._przebieg` |
| 255 | `uniesie_artykul._pusty(s)` | — | — | `artykul_z_puli.uniesie_artykul` |
| 268 | `wybierz_fakt(conn, run_id, ile)` | — | Swiezy fakt z puli ciekawostek, ktory NIE powtarza zadnego artykulu. | `artykul_z_puli._przebieg` |
| 352 | `main()` | DB | Otwiera przebieg, oddaje robote i ZAMYKA go — takze przy wyjatku. | `artykul_z_puli (poziom modulu)` |
| 442 | `_zrob_miejsce_na_fakt(card)` | — | Robi miejsce na wstrzykniete twierdzenie, nie tracac zadnego ZRODLA. | `artykul_z_puli._przebieg` |
| 473 | `_zrob_miejsce_na_fakt._host(c)` | — | — | `artykul_z_puli._zrob_miejsce_na_fakt` |
| 492 | `_rozszerz_najstarsze(card, data_faktu)` | — | Data wstrzyknietego zrodla wazy — ale TYLKO w strone ostrzezenia. | `artykul_z_puli._przebieg` |
| 522 | `_przebieg(conn, run_id)` | DB | — | `artykul_z_puli.main` |
| 974 | `_katalog_ratunku()` | — | Katalog OBOK `ARTICLES_DIR`, nigdy w nim. | `artykul_z_puli._ratuj_tekst` |
| 1005 | `_opublikuj(sciezka)` | WWW | Wystawia gotowy artykul, probujac wiecej niz raz. | `artykul_z_puli._napisz_i_zapisz` |
| 1057 | `_ramka(powod, brak, katalog)` | — | Ostrzezenie, ktore idzie na POCZATEK `.md`, a nie tylko obok niego. | `artykul_z_puli._ratuj_tekst` |
| 1129 | `_zrodla(card)` | — | Sekcja `## Sources` — bez pytania bazy o nazwy zrodel. | `artykul_z_puli._ratuj_tekst` |
| 1147 | `_ratuj_tekst(run_id, brief, card, draft, etap, exc, raport)` | — | Gotowy tekst na dysk, gdy budzet albo wylacznik przerywa PO pisaniu. | `artykul_z_puli._napisz_i_zapisz` |
| 1272 | `_napisz_i_zapisz(conn, run_id, brief, card)` | — | Od bramki „warto pisac" do zapisu i grafiki. | `artykul_z_puli._przebieg` |

---

<a id="agent-v2audyt-kosztow-py"></a>
## `agent-v2/audyt_kosztow.py`

Read-only audit of the API ledger, research sources and editorial memory.

4 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 15 | `_json(path, default)` | — | — | `audyt_kosztow.collect` |
| 22 | `_failure(note)` | — | — | `audyt_kosztow.collect` |
| 34 | `collect(directory, min_run)` | DB | — | `audyt_kosztow.main` |
| 134 | `main()` | — | — | `audyt_kosztow (poziom modulu)` |

---

<a id="agent-v2audyt-researchu-py"></a>
## `agent-v2/audyt_researchu.py`

Audyt segmentu researchu na ZYWYCH danych, jednym poleceniem.

3 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 41 | `etap(nr, nazwa)` | — | — | `audyt_researchu.main` |
| 48 | `werdykt(nazwa, stan, szczegol)` | — | — | `audyt_researchu.main` |
| 53 | `main()` | — | — | `audyt_researchu (poziom modulu)` |

---

<a id="agent-v2audyt-systemu-py"></a>
## `agent-v2/audyt_systemu.py`

Audyt CALEGO systemu na zywych danych, jednym poleceniem.

9 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 149 | `czy_pominiecie(rodzaj)` | — | Czy ten wpis jest pominieciem. | `audyt_systemu.main`, `audyt_systemu.policz_rodzaje` |
| 154 | `policz_rodzaje(wpisy)` | — | (udane, nieudane, pominiete) — trzy liczniki, bo stany naprawde sa trzy. | `audyt_systemu.main` |
| 177 | `etap(nr, nazwa)` | — | — | `audyt_systemu.main` |
| 184 | `werdykt(nazwa, stan, szczegol)` | — | — | `audyt_systemu.main` |
| 189 | `dziennik()` | — | — | `audyt_systemu.main` |
| 206 | `dzien(w)` | — | — | `audyt_systemu.main` |
| 210 | `ocen_pomiary(pomiary, wpisy)` | — | Czy cokolwiek UMKNELO pomiarowi. | `audyt_systemu.main` |
| 233 | `ocen_pomiary.rodzaj_pomiaru(r)` | — | — | `audyt_systemu.ocen_pomiary` |
| 264 | `main()` | WWW | — | `audyt_systemu (poziom modulu)` |

---

<a id="agent-v2audyt-tematow-py"></a>
## `agent-v2/audyt_tematow.py`

Audyt segmentu tematow — kazdy etap na ZYWYCH danych, jednym poleceniem.

4 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 41 | `etap(nr, nazwa)` | — | — | `audyt_tematow.main` |
| 48 | `werdykt(nazwa, stan, szczegol)` | — | — | `audyt_tematow.main` |
| 53 | `bank()` | — | Indeks kandydatow, albo pusto — narzedzie audytowe NIE MOZE sie wywalac. | `audyt_tematow.main` |
| 77 | `main()` | — | — | `audyt_tematow (poziom modulu)` |

---

<a id="agent-v2bramki-py"></a>
## `agent-v2/bramki.py`

Co moze zatrzymac tresc — wyliczone z kodu, nie spisane z pamieci.

9 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 52 | `_moduly_agenta()` | — | Wszystkie moduly agenta, alfabetycznie. | `bramki (poziom modulu)` |
| 78 | `wystawienia_bez_pokrycia()` | — | Nazwy z `WYSTAWIENIA`, ktorych nie ma w zadnym module agenta. | `bramki.raport` |
| 97 | `_zrodlo(nazwa)` | — | — | `bramki.przerwania_w_petlach`, `bramki.warunki_przed_wystawieniem`, `bramki.wstrzymania_publikacji` |
| 109 | `_komentarz_nad(linie, nr, ile)` | — | Ostatnia linia komentarza nad wskazanym wierszem — zwykle uzasadnienie. | `bramki.przerwania_w_petlach`, `bramki.wstrzymania_publikacji` |
| 123 | `_rodzic_funkcji(drzewo)` | — | Mapa: numer wiersza -> nazwa funkcji, w ktorej ten wiersz lezy. | `bramki.przerwania_w_petlach`, `bramki.warunki_przed_wystawieniem`, `bramki.wstrzymania_publikacji` |
| 133 | `wstrzymania_publikacji(pelne)` | — | Kazde miejsce, ktore ustawia `safe_to_post` na falsz. | `bramki.raport` |
| 162 | `warunki_przed_wystawieniem(pelne)` | — | Kazde wystawienie tresci i warunki, pod ktorymi stoi. | `bramki.raport` |
| 206 | `przerwania_w_petlach()` | — | `continue` i `return` w petlach po kandydatach — czyli „ten odpada". | `bramki.raport` |
| 256 | `raport(pelne)` | — | — | `bramki (poziom modulu)` |

---

<a id="agent-v2browser-py"></a>
## `agent-v2/browser.py`

Czytanie stron przeglądarką — tam, gdzie zwykły HTTP nie wystarcza.

105 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 73 | `opis_bledu(exc, limit)` | — | Nazwa wyjatku i POWOD — nie sam naglowek. | `browser._klik_na_profilu`, `browser.kto_nas_czyta`, `browser.obserwuj_profil`, `browser.pobierz_subskrybentow` *(+10)* |
| 116 | `wymagaj_wlasciwego_konta(page)` | WWW | Verify the logged-in principal, independently of the public profile. | `browser._klik_na_profilu`, `browser.obserwuj_profil`, `browser.polub_w_kanale`, `browser.restackuj_w_kanale` *(+6)* |
| 162 | `wlasciwe_konto(page)` | DEAD? | — | — |
| 195 | `pod_rzad_nieudanych(rodzaj)` | DEAD? | Ile porazek tego rodzaju poszlo BEZPOSREDNIO po sobie w tym przebiegu. | — |
| 204 | `slad_przebiegu()` | DEAD? | Podsumowanie tego, co ten proces zrobil — do wypisania na koncu. | — |
| 217 | `dopisz_wynik(rodzaj, wynik, **szczegoly)` | — | Jeden wpis na dzialanie — takze wtedy, gdy sie NIE UDALO, i z powodem. | `browser._klik_na_profilu`, `browser.obserwuj_profil`, `browser.polec_publikacje`, `browser.wystaw_artykul` *(+7)* |
| 328 | `zapisz_w_dzienniku(rodzaj, **szczegoly)` | — | Dziennik DZIALAN, nie wywolan modelu. | `browser._klik_na_profilu`, `browser.dopisz_skutki`, `browser.dopisz_wynik`, `browser.obserwuj_profil` *(+5)* |
| 352 | `z_dziennika_dzis()` | — | Ile komentarzy i polubien poszlo dzis — wedlug naszego zapisu. | `browser.ile_dzis_wystawione` |
| 418 | `naprawde_wyslac(wyslij, co)` | — | Ostatnie sito przed KAZDYM dzialaniem widocznym publicznie. | `browser._klik_na_profilu`, `browser.obserwuj_profil`, `browser.polec_publikacje`, `browser.polub_w_kanale` *(+7)* |
| 451 | `zalogowany(context)` | WWW | Twarde sprawdzenie: albo jest ciasteczko sesji, albo go nie ma. | `browser.sprawdz_serwer`, `browser.sprawdz_sesje`, `browser.zaloguj` |
| 456 | `dni_do_wygasniecia()` | — | Ile dni zostało sesji. | `alarm.sprawdz_sesje_i_ostrzez`, `browser.sprawdz_serwer`, `browser.sprawdz_sesje`, `browser.wymagaj_sesji` |
| 475 | `wymagaj_sesji()` | — | Sprawdza sesję przed pracą i mówi wprost, gdy trzeba się zalogować. | `browser._klik_na_profilu`, `browser.dopisz_skutki`, `browser.ile_dzis_wystawione`, `browser.kogo_polecamy` *(+22)* |
| 509 | `_chrome_odpowiada()` | — | — | `browser.podlacz_sie`, `browser.uruchom_chrome` |
| 519 | `uruchom_chrome()` | — | Otwiera Chrome na trwałym profilu agenta, jeśli jeszcze nie działa. | `browser.podlacz_sie` |
| 551 | `rozgrzej(context)` | WWW | Pozwala Cloudflare wydać zgodę dla adresu, z którego akurat działamy. | `browser.podlacz_sie` |
| 594 | `plaski(tekst)` | — | Tekst sprowadzony do znakow, ktore SAMI piszemy — do POROWNYWANIA. | `browser.numer_naszej_notki`, `browser.potwierdz_artykul`, `browser.potwierdz_komentarz`, `browser.potwierdz_odpowiedz` |
| 624 | `api_json(page, sciezka, baza)` | WWW | Czyta API WCHODZĄC na adres, zamiast wołać `fetch` ze strony. | `browser._artykuly_z_panelu`, `browser._klik_na_profilu`, `browser._watek_z_paginacja`, `browser.dopisz_skutki` *(+20)* |
| 659 | `podlacz_sie()` | WWW | Podłącza się do Chrome'a, którego uruchomił i zalogował WŁAŚCICIEL. | `browser._klik_na_profilu`, `browser.dopisz_skutki`, `browser.ile_dzis_wystawione`, `browser.kogo_polecamy` *(+25)* |
| 756 | `sprawdz_sesje()` | WWW | Czy Chrome właściciela jest zalogowany i co agent w nim widzi. | `browser (poziom modulu)` |
| 796 | `sprawdz_serwer()` | WWW | Odpowiada na JEDNO pytanie: czy zapisana sesja żyje z adresu tego serwera. | `browser (poziom modulu)` |
| 844 | `zaloguj()` | WWW | Otwiera prawdziwe okno przeglądarki i czeka, aż właściciel się zaloguje. | `browser (poziom modulu)` |
| 901 | `rozpoznanie()` | WWW | Sprawdza, czy agent umie się poruszać po zalogowanym koncie. | `browser (poziom modulu)` |
| 973 | `_plaskie(galaz)` | — | Rozwija gałąź wątku do płaskiej listy komentarzy. | `browser._watek_z_paginacja`, `browser.juz_sie_odezwalismy`, `browser.nieodpowiedziane`, `browser.odpowiedzi_na_nasze_komentarze` *(+1)* |
| 988 | `_kiedy(c)` | — | — | `browser.komentarze_pod_artykulami`, `browser.nieodpowiedziane`, `browser.odpowiedzi_na_nasze_komentarze` |
| 997 | `ile_dzis_wystawione()` | WWW | Ile notek, komentarzy i polubien poszlo dzisiaj. | `run.dzien` |
| 1065 | `statystyki_pozycji(pozycje)` | WWW | Pobiera statystyki NASZYCH tresci — jedna przegladarka na cala liste. | `run.dzien`, `run.dzien.odpowiedzi` |
| 1185 | `_ludzie_z_zakladki_ze_stanem(page)` | WWW | Kto jest na tej zakladce ORAZ czy zakladke w ogole udalo sie odczytac. | `browser._ludzie_z_zakladki`, `browser.kto_nas_czyta` |
| 1216 | `_ludzie_z_zakladki(page)` | — | Sama lista ludzi z zakladki. | `browser.odswiez_kogo_obserwujemy` |
| 1221 | `kto_nas_czyta(page)` | WWW | KTO nas obserwuje i subskrybuje — imiennie i z data. | `browser.zapisz_czytelnikow` |
| 1320 | `zapisz_czytelnikow(page)` | — | Zrzut listy czytelnikow do pliku, jeden wiersz na wywolanie. | `browser.nasze_pozycje_do_pomiaru` |
| 1417 | `kogo_obserwujemy()` | — | Kogo juz obserwujemy — Z DYSKU, BEZ SIECI. | `browser.czy_juz_obserwujemy`, `browser.odswiez_kogo_obserwujemy`, `browser.zapamietaj_obserwowanego`, `run.dzien` *(+2)* |
| 1444 | `_zapisz_kogo_obserwujemy(pamiec)` | — | Nigdy nie przerywa dzialania — to pamiec pomocnicza, nie warunek pracy. | `browser.odswiez_kogo_obserwujemy`, `browser.zapamietaj_obserwowanego` |
| 1457 | `zapamietaj_obserwowanego(uchwyt, host)` | — | Dopisuje JEDNEGO do pamieci — po udanej obserwacji albo po zastaniu „Unfollow" w menu. | `browser.obserwuj_profil`, `run.dzien`, `run.dzien.obserwuj` |
| 1480 | `czy_juz_obserwujemy(host, pamiec)` | — | Czy ten HOST wskazuje kogos, kogo juz obserwujemy. | `run.dzien`, `run.dzien.obserwuj` |
| 1500 | `odswiez_kogo_obserwujemy(page)` | WWW | Przepisuje pamiec ze strony `/@my/following`. | `browser.nasze_pozycje_do_pomiaru` |
| 1540 | `zapisz_wzrost_konta(profil)` | — | Ilu nas czyta DZISIAJ — jedna linia na pomiar, historia zostaje. | `browser.nasze_pozycje_do_pomiaru` |
| 1627 | `_wiersze_zrodel(dane)` | — | Lista pozycji z odpowiedzi o zrodlach — niezaleznie od klucza. | `browser._zapisy_ogolem`, `browser.zapisz_zrodla_ruchu` |
| 1640 | `_cos_w_odpowiedzi(dane)` | — | Czy odpowiedz W OGOLE cos niesie — odroznia „pusto" od „nie wiem". | `browser.zapisz_zrodla_ruchu` |
| 1665 | `_suma_pola(wiersze, *pola)` | — | Suma pierwszego istniejacego pola po wierszach. | `browser._z_totali`, `browser._zapisy_wezla`, `browser.zapisz_zrodla_ruchu` |
| 1686 | `_z_miar(wezel, nazwy)` | — | Liczba z `metrics: [{"name": "Subscribers", "total": 5}, ...]`. | `browser._z_totali`, `browser._zapisy_wezla` |
| 1704 | `_zapisy_wezla(wezel)` | — | Zapisy z jednej galezi — obojetne, w ktorym z dwoch ksztaltow przyszly. | `browser._zapisy_ogolem`, `browser._zapisy_per_notka` |
| 1711 | `_z_totali(dane, nazwy)` | — | Liczba z pola `totals` — panel podaje je LISTA, nie slownikiem. | `browser._zapisy_ogolem`, `browser.zapisz_zrodla_ruchu` |
| 1724 | `_zapisy_ogolem(dane)` | — | Laczna liczba zapisow z drzewa `growth/sources`, albo `None`. | `browser.zapisz_zrodla_ruchu` |
| 1740 | `_zapisy_per_notka(dane)` | — | {numer notki: zapisy} — z dowolnie zagniezdzonego drzewa. | `browser.zapisz_zrodla_ruchu` |
| 1765 | `zapisz_zrodla_ruchu(page, dni)` | WWW | SKAD naprawde biora sie zapisy — tabela zrodel, jedna linia na odczyt. | `browser.statystyki_pozycji` |
| 1969 | `_artykuly_z_panelu(page, baza)` | — | Nasze artykuly razem ze statystykami — JEDNYM zapytaniem. | `browser.nasze_pozycje_do_pomiaru` |
| 2014 | `_artykuly_z_panelu.licz(*klucze)` | — | — | `browser._artykuly_z_panelu` |
| 2051 | `nasze_pozycje_do_pomiaru(page, ile)` | — | Co wystawilismy i ma wlasny numer — czyli co da sie zmierzyc. | `browser.statystyki_pozycji` |
| 2216 | `dopisz_skutki()` | WWW | Dopisuje do dziennika, CO Z NASZYCH DZIALAN WYNIKLO. | `run.dzien`, `run.dzien.odpowiedzi` |
| 2367 | `odpowiedzi_na_nasze_komentarze(ile)` | WWW | Odpowiedzi na NASZE komentarze zostawione pod CUDZYMI tekstami. | `run.dzien`, `run.dzien.odpowiedzi` |
| 2479 | `komentarze_pod_artykulami(ile)` | WWW | Cudze komentarze pod NASZYMI artykulami, na ktore nie odpisalismy. | `run.dzien`, `run.dzien.odpowiedzi` |
| 2536 | `nieodpowiedziane(ile)` | WWW | Cudze odpowiedzi pod naszymi notkami, na które jeszcze nie odpisaliśmy. | `run.dzien`, `run.dzien.odpowiedzi` |
| 2595 | `sluchaj_publikacji(page)` | WWW | Zbiera kody odpowiedzi na zapytania PUBLIKUJACE. | `browser.wystaw_notke` |
| 2612 | `id_z_odpowiedzi(odpowiedzi)` | — | Identyfikator notki, ktory Substack oddal przy zapisie. | `browser.wystaw_notke` |
| 2645 | `numer_naszej_notki(page, tekst, prob)` | WWW | Numer notki odczytany z NASZEGO PROFILU po jej tresci. | `browser.potwierdz_notke`, `browser.restackuj_w_kanale`, `browser.wystaw_notke` |
| 2681 | `potwierdz_notke(page, tekst, prob)` | — | Pyta Substacka, czy notka naprawdę wisi na naszym profilu. | `browser.wystaw_notke` |
| 2712 | `_autor_przy_przycisku(przycisk)` | — | Kto napisal wpis, przy ktorym stoi ten przycisk. | `browser.polub_w_kanale`, `browser.restackuj_w_kanale` |
| 2761 | `_uchwyt_wezla(lokator)` | — | Uchwyt do KONKRETNEGO wezla DOM, albo None. | `browser.polub_w_kanale` |
| 2775 | `_stan_przycisku(uchwyt)` | — | Jak przycisk wyglada — wszystkie sygnaly naraz, sklejone w jeden napis. | `browser.polub_w_kanale`, `browser.potwierdz_polubienie` |
| 2800 | `potwierdz_polubienie(uchwyt, przed)` | — | Czy przycisk po klknieciu wyglada inaczej niz przed nim. | `browser.polub_w_kanale` |
| 2831 | `polub_w_kanale(ile, wyslij, url)` | WWW | Polubienia w kanale czytelnika. | `run.dzien`, `run.dzien.polubienia` |
| 2965 | `konto_za_duze(handle)` | — | Czy konto przekracza sufit odbiorcow — SPRAWDZANE ZANIM ZAPLACIMY CZAS. | `run.dzien`, `run.dzien.subskrybuj` |
| 3053 | `_klik_na_profilu(handle, napisy, rodzaj, wyslij)` | WWW | Klika JEDEN konkretny przycisk na cudzym profilu — i tylko jego. | `browser.zasubskrybuj` |
| 3161 | `_wybierz_darmowy_plan(page)` | WWW | Finish an explicitly free plan; never select a paid/default plan. | `browser._klik_na_profilu` |
| 3188 | `pobierz_subskrybentow()` | WWW | Czyta liste subskrybentow z WLASNEGO panelu, wlasna sesja. | `kopia_subskrybentow.pobierz_z_panelu` |
| 3258 | `zloz_wiersze_subskrybentow(surowe)` | — | Sklada wiersze z komorek tabeli panelu: adres, typ i data rozpoczecia. | `browser._wiersze_subskrybentow` |
| 3296 | `_wiersze_subskrybentow(page)` | WWW | Czyta komorki tabeli z panelu i oddaje je zlozone. | `browser.pobierz_subskrybentow` |
| 3360 | `_pozycje_menu(page)` | WWW | Teksty pozycji OTWARTEGO menu, w kolejnosci ekranu. | `browser.obserwuj_profil`, `browser.potwierdz_obserwacje` |
| 3379 | `_otworz_menu_profilu(page)` | WWW | Klika kolko „..." w naglowku profilu. | `browser.obserwuj_profil`, `browser.potwierdz_obserwacje` |
| 3401 | `potwierdz_obserwacje(page)` | WWW | Czy menu profilu mowi teraz, ze go OBSERWUJEMY. | `browser.obserwuj_profil` |
| 3470 | `obserwuj_profil(handle, wyslij)` | WWW | Obserwuje cudzy profil — jego notki trafiaja do naszego kanalu. | `run.dzien`, `run.dzien.obserwuj` |
| 3642 | `kogo_polecamy(page)` | WWW | Kogo nasza publikacja poleca — z API, nie z pamieci. | `browser.polec_publikacje` |
| 3674 | `polec_publikacje(fraza, powod, wyslij)` | WWW DEAD? | Dodaje REKOMENDACJE publikacji. | — |
| 3781 | `zasubskrybuj(handle, wyslij)` | — | Subskrybuje cudzy profil. | `run.dzien`, `run.dzien.subskrybuj` |
| 3787 | `_esc(t)` | — | — | `browser._html_z_linkami`, `browser.rozbierz_artykul` |
| 3791 | `_html_z_linkami(tekst)` | — | Render inline HTTP(S) Markdown links while escaping all source text. | `browser.rozbierz_artykul` |
| 3803 | `rozbierz_artykul(sciezka)` | — | Rozkłada plik artykułu na tytuł, podtytuł i treść jako HTML. | `browser.wystaw_artykul` |
| 3886 | `wypelnij_artykul(page, artykul, obraz)` | WWW | Wkłada tytuł, podtytuł, grafikę i treść do otwartego edytora. | `browser.wystaw_artykul` |
| 3931 | `wstaw_przycisk_subskrypcji(page)` | WWW | Jeden przycisk subskrypcji, po ostatnim akapicie a przed źródłami. | `browser.wypelnij_artykul` |
| 3968 | `tresc_oswiadczenia()` | — | Oświadczenie „Jak to robię" — z pliku, nie z drugiej kopii w kodzie. | `browser.ustaw_oswiadczenie_ai` |
| 3989 | `ustaw_oswiadczenie_ai(wyslij)` | WWW | Ustawia stałe oświadczenie pokazywane każdemu, kto skanuje nas pod kątem AI. | `browser (poziom modulu)` |
| 4067 | `wystaw_odpowiedz_pod_artykulem(url_artykulu, autor, tekst, wyslij)` | WWW | Odpowiada pod KONKRETNYM komentarzem pod naszym artykułem. | `run.dzien`, `run.dzien.odpowiedzi` |
| 4191 | `potwierdz_artykul(page, tytul)` | — | Pyta Substacka, czy artykuł naprawdę jest opublikowany. | `browser._potwierdz_wysylke_artykulu`, `browser.wystaw_artykul` |
| 4201 | `_domknij_publikacje_artykulu(page)` | WWW | Complete Substack's optional subscribe-button prompt after Send. | `browser._potwierdz_wysylke_artykulu`, `browser.wystaw_artykul` |
| 4212 | `_potwierdz_wysylke_artykulu(page, tytul)` | WWW | Retry reads, never the send; keep the editor open for a late prompt. | `browser.wystaw_artykul` |
| 4231 | `wystaw_artykul(sciezka_md, sciezka_png, wyslij)` | WWW | Wystawia artykuł na Substacku. | `artykul_z_puli._opublikuj`, `run.main` |
| 4347 | `_watek_z_paginacja(page, nid, stron)` | — | Caly watek notki — ze WSZYSTKICH stron, nie tylko z pierwszej. | `browser.potwierdz_komentarz`, `browser.potwierdz_odpowiedz` |
| 4380 | `potwierdz_odpowiedz(page, note_id, tekst)` | WWW | Pyta Substacka, czy nasza odpowiedź naprawdę jest w wątku — i KTORA. | `browser.wystaw_odpowiedz` |
| 4416 | `wystaw_odpowiedz(note_id, tekst, wyslij, kontekst, rodzaj)` | WWW | Odpowiada w watku — pod nasza notka albo w cudzej dyskusji. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.odpowiedzi` |
| 4597 | `wystaw_notke(tekst, wyslij, typ, forma, model)` | WWW | Wystawia notkę. | `run.dzien`, `run.dzien.notki` |
| 4728 | `zapamietaj_platny_host(host, prawo)` | — | Host, ktory wprost mowi, ze komentowac moga tylko placacy. | `browser.mozna_komentowac` |
| 4755 | `hosty_tylko_dla_placacych()` | — | Hosty, gdzie komentowac moga tylko placacy — do odsiania PRZED ocena. | `audyt_systemu.main`, `run.dzien`, `run.dzien.komentarze` |
| 4769 | `zapomnij_platny_host(host)` | — | Udany komentarz kasuje host z listy — wydawca mogl zmienic ustawienia. | `run.dzien`, `run.dzien.komentarze` |
| 4814 | `hosty_gdzie_komentarz_nie_wchodzi(min_prob, dni)` | — | Hosty, gdzie w ostatnich `dni` dniach probowalismy >=2 razy i ANI RAZ komentarz nie wszedl. | `browser.mozna_komentowac`, `run.dzien`, `run.dzien.komentarze` |
| 4934 | `mozna_komentowac(url)` | WWW | Czy pod tym tekstem wolno nam w ogóle napisać. | `run.dzien`, `run.dzien.komentarze` |
| 5002 | `uchwyt_publikacji(host)` | WWW | Nazwa konta do obserwowania — z hosta albo, gdy trzeba, z API. | `run.dzien`, `run.dzien.obserwuj`, `run.dzien.subskrybuj` |
| 5042 | `juz_sie_odezwalismy(page, url)` | — | Czy JUZ napisalismy cokolwiek pod tym postem albo pod ta notka. | `browser.wystaw_komentarz` |
| 5093 | `bez_znacznikow(html)` | — | Sam tekst, bez HTML-a. | `browser.wystaw_artykul` |
| 5103 | `potwierdz_adres_artykulu(page, tytul)` | — | Prawdziwy adres opublikowanego artykulu — od Substacka, nie z tytulu. | `browser.wystaw_artykul` |
| 5136 | `potwierdz_komentarz(page, url, tekst)` | WWW | Pyta Substacka, czy komentarz naprawdę wisi — zamiast wierzyć kliknięciu. | `browser.wystaw_komentarz`, `browser.wystaw_odpowiedz_pod_artykulem` |
| 5208 | `wystaw_komentarz(url, tekst, wyslij, kontekst)` | WWW | Wystawia komentarz pod cudzym postem. | `run.dzien`, `run.dzien.komentarze` |
| 5440 | `read_pages(urls)` | — | Read sources with a deadline that also covers browser shutdown. | `run.dzien`, `run.dzien.komentarze`, `stages._dobierz_przegladarka` |
| 5446 | `restackuj_w_kanale(ile, decyzja, wyslij, url)` | WWW | Podaje dalej cudze notki z wlasnym zdaniem. | `run.dzien`, `run.dzien.restacki` |
| 5637 | `w_rewirze(tekst)` | — | Czy cudza notka jest o tym, o czym pisze ta publikacja — po znakach niszy. | `browser.polub_w_kanale`, `browser.restackuj_w_kanale` |
| 5655 | `_notka_przy_przycisku(przycisk)` | — | Tresc i autor notki, przy ktorej stoi ten przycisk. | `browser.polub_w_kanale`, `browser.restackuj_w_kanale` |

---

<a id="agent-v2browser-reader-py"></a>
## `agent-v2/browser_reader.py`

Bound source reads, including Playwright shutdown, in an owned subprocess.

5 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 14 | `_stop_owned_process(process)` | — | — | `browser_reader._collect` |
| 36 | `_results(path)` | — | — | `browser_reader._collect` |
| 50 | `_collect(command, urls, output, timeout)` | — | — | `browser_reader.read_pages` |
| 73 | `read_pages(urls)` | DEAD? | — | — |
| 90 | `_worker(input_path, output)` | WWW | — | `browser_reader (poziom modulu)` |

---

<a id="agent-v2call-runtime-py"></a>
## `agent-v2/call_runtime.py`

Per-operation deadlines and usage; workers never write to the database.

10 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 27 | `Attempt.check(self)` | DEAD? | — | — |
| 36 | `observe()` | DEAD? | — | — |
| 43 | `capture(usage, provider)` | DEAD? | — | — |
| 47 | `capture.get(name, default)` | — | — | `call_runtime.capture` |
| 74 | `token_limit(default)` | DEAD? | — | — |
| 79 | `check()` | DEAD? | — | — |
| 85 | `watch(resource)` | DEAD? | — | — |
| 93 | `invoke(state, fn)` | WWW DEAD? | Bound even a transport that blocks; close it without blocking the caller. | — |
| 100 | `invoke.worker()` | — | — | `call_runtime.invoke` |
| 124 | `invoke.safe_close(fn)` | — | — | `call_runtime.invoke` |

---

<a id="agent-v2config-py"></a>
## `agent-v2/config.py`

Jedyne miejsce ze stałymi.

44 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 58 | `_korpus_stylu()` | — | — | `config (poziom modulu)` |
| 99 | `_env(name, default)` | — | — | `config (poziom modulu)`, `config._aktywacja_przy_starcie` |
| 481 | `stawka_deepseek(model, kiedy)` | — | Stawka DeepSeeka z uwzglednieniem pory doby po wejsciu nowej taryfy. | `llm._cost` |
| 508 | `pora_na_publikacje(kiedy)` | — | Czy teraz wolno wystawiac NOTKI — wg zegara CZYTELNIKOW, nie serwera. | `run.dzien` |
| 554 | `w_szczycie(kiedy)` | — | Czy teraz obowiazuje droga taryfa. | `config.stawka_deepseek` |
| 580 | `narzedzie_wyszukiwania(model)` | — | Nazwa narzedzia wyszukiwania i ewentualne ostrzezenie. | `llm._narzedzie_wyszukiwania` |
| 649 | `_dzis_utc()` | — | Dzisiejszy dzien UTC. | `config (poziom modulu)` |
| 671 | `sufit_dnia(dzien)` | — | Sufit obowiazujacy W TYM DNIU, nie dzisiaj. | `alarm.koszt`, `config (poziom modulu)` |
| 855 | `kotwica_dlugosci(glebokosc)` | — | Zdanie kalibrujace dlugosc, dobrane do ilosci materialu. | `stages.write` |
| 860 | `dlugosc_dla(glebokosc)` | — | Ile slow ma miec artykul o tej glebokosci. | `artykul_z_puli._napisz_i_zapisz`, `run.main`, `stages.write` |
| 1027 | `_tokens_for(chars)` | — | — | `config (poziom modulu)` |
| 1129 | `dlugosc_notki(typ)` | — | Przedział słów dla tego typu notki. | `stages.note` |
| 1397 | `losowa_postawa()` | — | Ktora postawa dla TEGO komentarza. | `stages.comment_on` |
| 1445 | `otwarcia_dla_postawy(postawa)` | — | Otwarcia, ktore ta postawa ma jak wykonac. | `config.losowe_otwarcie` |
| 1455 | `losowe_otwarcie(postawa)` | — | — | `stages.comment_on`, `stages.reply_to` |
| 1461 | `losowa_dlugosc()` | — | Ile slow ma miec ta konkretna wypowiedz. | `stages.comment_on`, `stages.reply_to` |
| 1604 | `formy_dla_typu(typ)` | — | Formy, ktore ten typ notki ma czym wypelnic. | `stages.notki_dnia` |
| 1905 | `losowy_ksztalt_mysli()` | — | Ktory ksztalt dostaje ta MYSL. | `stages._opis_typu` |
| 2062 | `normy_dzienne()` | — | Ile czego POWINNO wychodzic dziennie — srodek widelek. | `alarm.bank_bez_tematow`, `alarm.max_dzialan_dziennie`, `audyt_systemu.main`, `norma.main` *(+1)* |
| 2150 | `_cisza_z_hasza(dzien)` | — | — | `config.cichy_dzien` |
| 2157 | `cichy_dzien(kiedy)` | — | Czy dzis nie nadajemy. | `audyt_systemu.main`, `norma.main`, `run.dzien`, `stages.podsumowanie_dzialan` |
| 2231 | `dzis_dzien_artykulu(kiedy)` | — | Czy dzis (UTC) jest dzien artykulu wedlug harmonogramu presetu. | `artykul_z_puli.main` |
| 2241 | `zegar_agenta_on_calendar()` | DEAD? | Linie `OnCalendar=` zegara rutyny dnia, z harmonogramu presetu. | — |
| 2247 | `zegar_artykulu_on_calendar()` | DEAD? | Linie `OnCalendar=` zegara artykulu; pusta lista, gdy artykulow nie ma. | — |
| 2638 | `sufit_wyjscia(purpose, model)` | — | Sufit wyjscia dla TEGO modelu, nie dla nazwy etapu. | `llm._call_claude`, `llm._call_deepseek`, `llm._call_openai_responses` |
| 2674 | `timeout_for(max_tokens)` | — | Termin w sekundach, który realnie pokrywa podany sufit tokenów. | `llm._call_claude`, `llm._call_deepseek`, `llm._call_deepseek_responses`, `llm._call_openai_responses` |
| 2752 | `_znacznik_klienta(marka)` | — | — | `config._naglowek_klienta` |
| 2782 | `tylko_dla_wlasciciela(sciezka)` | — | Prawa 0600 na tym pliku — a gdzie sie nie da, MOWI o tym raz. | `browser.rozpoznanie`, `browser.sprawdz_sesje`, `browser.zaloguj`, `config.otworz_tylko_dla_wlasciciela` |
| 2812 | `otworz_tylko_dla_wlasciciela(sciezka, tryb)` | — | Otwiera plik do zapisu TWORZAC GO od razu z prawami 0600. | `kopia_subskrybentow.main`, `kopia_subskrybentow.pobierz_z_panelu` |
| 2847 | `pytanie_o_stan_dziedziny()` | — | O co pytamy, sprawdzajac stan dziedziny. | `aktualne_modele.pobierz`, `aktualne_modele.wczytaj` |
| 2922 | `usluga_agenta()` | — | Nazwa pliku uslugi, ktora uruchamia dzien agenta — po TRESCI, nie nazwie. | `alarm.sprawdz_przebiegi_i_ostrzez`, `config.zegar_agenta` |
| 2945 | `zegar_agenta()` | DEAD? | Sciezka do jednostki zegara agenta albo None. | — |
| 2954 | `_naglowek_klienta()` | — | Naglowek User-Agent zlozony z BIEZACEJ nazwy marki. | `config (poziom modulu)` |
| 2983 | `_w_darmowym_tescie()` | — | Czy uruchomiony program to test, ktory NIE MA prawa placic. | `config (poziom modulu)` |
| 3038 | `pod_produkcyjnymi_danymi(sciezka)` | — | Czy ta sciezka lezy w PRAWDZIWYM katalogu danych (takze w podkatalogu). | `db._odmow_produkcji` |
| 3053 | `_moduly_projektu()` | — | Zaimportowane moduly z `agent-v2/`, bez samych testow. | `config.uzyj_katalogu_danych` |
| 3074 | `uzyj_katalogu_danych(katalog, utworz)` | — | Przestawia `DATA_DIR` I KOMPLET sciezek z niego policzonych. | `config (poziom modulu)` |
| 3102 | `uzyj_katalogu_danych.przeniesiona(wartosc)` | — | Ta sama sciezka wzgledem NOWEGO katalogu — albo None, gdy nie nasza. | `config.uzyj_katalogu_danych` |
| 3137 | `przywroc_katalog_danych(zdjecie)` | DEAD? | Cofa `uzyj_katalogu_danych`. | — |
| 3268 | `losowy_ruch_koncowy()` | — | Czym konczy sie TEN artykul. | `stages.write` |
| 3276 | `losowa_liczba_paraleli(glebokosc, dostepne)` | — | Ile paraleli w drugim akcie. | `stages.write` |
| 3390 | `losowe_generatory(ile)` | — | Ktore wzorce w tym przebiegu. | `stages.znajdz_ciekawostki` |
| 3413 | `co_teraz_w_reku(kiedy, kalendarz)` | — | Rzeczy, ktorych czytelnik dotyka wlasnie teraz. | `stages.znajdz_ciekawostki` |
| 3517 | `_aktywacja_przy_starcie()` | — | — | `config (poziom modulu)` |

---

<a id="agent-v2db-py"></a>
## `agent-v2/db.py`

Baza: cztery tabele, waskie migracje kolumn, zero triggerow i limitow CHECK.

15 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 40 | `kanal(nazwa)` | — | Na czas bloku kazde zapisane wywolanie dostaje `akcja = nazwa`. | `stages._na_kanal`, `stages._na_kanal.zewnetrzny`, `stages._na_kanal.zewnetrzny.wewnetrzny`, `stages.przygotuj_artykul_do_publikacji` |
| 115 | `now()` | — | — | `db.available_budget`, `db.finish_run`, `db.record_call`, `db.start_attempt` *(+9)* |
| 123 | `_odmow_produkcji(db_path)` | — | GLOSNA odmowa: wyjatek, nie ciche pominiecie. | `db.connect` |
| 167 | `connect(path)` | — | Otwiera bazę i zakłada schemat, jeśli go nie ma. | `alarm._polaczenie`, `alarm.sprawdz_przebiegi_i_ostrzez`, `artykul_z_puli.main`, `norma.przebiegow_dzis` *(+1)* |
| 206 | `_dopisz_brakujace_kolumny(conn)` | DB | — | `db.connect` |
| 224 | `start_run(conn, stage, tryb)` | DB | Nowy przebieg. | `artykul_z_puli.main`, `run.main` |
| 264 | `tryb_przebiegu(conn, run_id)` | DB | Tor, do ktorego nalezy przebieg. | `db.available_budget`, `llm._preflight` |
| 275 | `finish_run(conn, run_id, status, stage, note)` | DB | — | `alarm.zawieszone`, `artykul_z_puli.main`, `run._done`, `run.main` |
| 287 | `record_call(conn, **fields)` | DB DEAD? | Zapisuje wywołanie, wstawiając TYLKO te kolumny, które ktoś podał. | — |
| 322 | `budget_used(conn, run_id, prefix, tryb)` | DB | Known spend plus outstanding/unknown reservations, counted only once. | `db.available_budget`, `run._summary` |
| 341 | `available_budget(conn, run_id)` | — | — | `llm._reserve_attempt` |
| 354 | `start_attempt(conn, reserved_usd, **fields)` | DB | Caller holds BEGIN IMMEDIATE while checking and reserving the budget. | `llm._reserve_attempt` |
| 366 | `finish_attempt(conn, call_id, **fields)` | DB | — | `llm._settle_attempt`, `llm._settle_image` |
| 376 | `spent_usd(conn, since_prefix, tryb)` | DB | Suma kosztów od znacznika czasu zaczynającego się danym prefiksem. | `alarm.koszt`, `llm._preflight`, `run.main` |
| 399 | `recent_domains(conn, limit)` | DB | Domeny z ostatnich N artykułów — wejście do reguły różnorodności. | `artykul_z_puli._przebieg`, `run.main` |

---

<a id="agent-v2feed-cache-py"></a>
## `agent-v2/feed_cache.py`

Per-instance, per-URL feed recovery.

2 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 17 | `_valid(body)` | — | — | `feed_cache.fetch` |
| 26 | `fetch(directory, url, request, now)` | — | Return validated XML and provenance; never refresh cache age on failure. | `korpus_kanalow.korpus_kanalow` |

---

<a id="agent-v2gates-py"></a>
## `agent-v2/gates.py`

Bramki wykrywaja naruszenia, ale zadna nie blokuje artykulu.

22 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 71 | `_digit_tokens(text)` | — | — | `gates._korpus_pobranych`, `gates.deterministic_floors`, `gates.numbers_outside_corpus` |
| 75 | `_niepobrane(card)` | — | Twierdzenia oznaczone `not_fetched` — dolozone, nie wyciagniete. | `gates.deterministic_floors` |
| 87 | `_korpus_pobranych(card)` | — | Liczby z materialu, ktory NAPRAWDE pobralismy. | `gates.numbers_outside_corpus` |
| 128 | `numbers_outside_corpus(body, card)` | — | Liczby w tekście, których nie ma nigdzie w POBRANYM materiale. | `gates.deterministic_floors` |
| 147 | `deterministic_floors(body, card, poprzednie)` | — | Podłogi bez modelu: 0 USD, milisekundy, zero wywołań. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 244 | `_akapity(body)` | — | — | `gates.niewiadome_na_koncu`, `gates.odcisk_formy`, `gates.zakazane_otwarcie` |
| 250 | `zastrzezenia(body)` | — | Zastrzezenia w pierwszej osobie. | `gates.deterministic_floors` |
| 255 | `zakazane_otwarcie(body)` | — | Pierwsze zdanie, jesli kaze czytelnikowi isc cos obejrzec. | `gates.deterministic_floors` |
| 264 | `statystyki_bez_zrodla(body)` | — | Zdania, ktore niosa liczbe i udaja, ze maja na nia zrodlo. | `gates.deterministic_floors` |
| 274 | `niewiadome_na_koncu(body)` | — | Zbiorczy akapit o niewiadomych w ostatniej trzeciej tekstu. | `gates.deterministic_floors`, `gates.odcisk_formy` |
| 302 | `odcisk_formy(body)` | — | Zgrubny szkielet tekstu — do porownania z poprzednimi, nie do oceny. | `gates.powtorzona_forma` |
| 319 | `odcisk_formy.kubelek(u)` | — | — | `gates.odcisk_formy` |
| 349 | `powtorzona_forma(body, poprzednie, prog)` | — | Czy ten tekst ma ksztalt ktoregos z poprzednich. | `gates.deterministic_floors` |
| 380 | `uwagi_z_formy(obserwacja, body)` | — | Zamienia obserwacje modelu w uwagi. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 469 | `pozycja_w_tekscie(cytat, body)` | — | Gdzie w tekście stoi ten cytat, jako ułamek długości. | `run.main` |
| 481 | `szerokosc_podstawy(card)` | — | Na ilu ODREBNYCH serwisach stoja potwierdzone twierdzenia. | `gates.deterministic_floors` |
| 517 | `frazy_z_instrukcji(body, dlugosc)` | — | Czy pisarz wklein do tekstu wlasne polecenie. | `gates.deterministic_floors` |
| 529 | `frazy_z_instrukcji.slowa_z(tekst)` | — | Slowa tekstu — LITERY W SENSIE UNICODE, nie alfabet angielski. | `gates.frazy_z_instrukcji` |
| 545 | `frazy_z_instrukcji.ciagi(slowa)` | — | — | `gates.frazy_z_instrukcji` |
| 572 | `verdict(findings)` | — | Artykuł powstaje ZAWSZE. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 587 | `zapowiedziany_akapit_granic(body)` | — | Czy akapit o granicach zaczyna sie od zdania o samym sobie. | `gates.deterministic_floors` |
| 649 | `artefakty_w_tekscie(body)` | — | Co w tym tekscie wyglada na blad programu, a nie na zdanie autora. | `artykul_z_puli._napisz_i_zapisz`, `personality._valid`, `stages.przygotuj_artykul_do_publikacji`, `stages.przygotuj_artykul_do_publikacji.guard` |

---

<a id="agent-v2insights-py"></a>
## `agent-v2/insights.py`

Read-only cost, outcome and research report.

12 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 13 | `moment(value)` | — | — | `insights.at_window`, `insights.collect`, `insights.collect.in_period`, `insights.graph_windows` |
| 21 | `number(value)` | — | — | `insights.at_window`, `insights.collect`, `insights.graph_windows` |
| 31 | `read_json(path, default)` | — | — | `insights.collect` |
| 38 | `rows(path, warnings)` | — | — | `insights.collect` |
| 58 | `at_window(records, published, hours, now, field)` | — | Latest measured value at/before the horizon, no more than 2h earlier. | `insights.collect` |
| 86 | `graph_windows(card, published, measured)` | DEAD? | Extract mature primary curves only; no invented values for missing windows. | — |
| 114 | `channel(value)` | — | — | `insights.collect` |
| 121 | `collect(directory, days, now)` | DB | — | `insights.main` |
| 146 | `collect.in_period(value)` | — | — | `insights.collect` |
| 150 | `collect.group()` | — | — | `insights.collect` |
| 224 | `collect.modified(path)` | — | — | `insights.collect` |
| 272 | `main()` | — | — | `insights (poziom modulu)` |

---

<a id="agent-v2interaction-history-py"></a>
## `agent-v2/interaction_history.py`

Skip confirmed interactions before paying to write them again.

3 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 8 | `target_key(value)` | — | — | `interaction_history.confirmed_targets`, `interaction_history.unhandled` |
| 26 | `confirmed_targets(directory)` | — | — | `interaction_history.unhandled` |
| 47 | `unhandled(posts, directory)` | — | Only confirmed target IDs are excluded; failed attempts remain eligible. | `stages.wybierz_cele` |

---

<a id="agent-v2jezyki-py"></a>
## `agent-v2/jezyki.py`

Wzorce bramek ZALEZNE OD JEZYKA — i glosny sprzeciw, gdy jezyka nie ma.

5 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 301 | `_ostrzez(jezyk, czego_brak)` | — | Raz na proces, ale GLOSNO. | `jezyki.frazy`, `jezyki.wzorzec` |
| 313 | `wzorzec(nazwa, jezyk)` | DEAD? | Skompilowany wzorzec bramki dla tego jezyka. | — |
| 322 | `frazy(nazwa, jezyk)` | DEAD? | Lista fraz dla tego jezyka. | — |
| 331 | `znane_jezyki()` | DEAD? | — | — |
| 335 | `brakujace(jezyk)` | — | Czego brakuje temu jezykowi wobec angielskiego. | `preset.sprawdz` |

---

<a id="agent-v2kanal-py"></a>
## `agent-v2/kanal.py`

Kanal czytelnika — jedyne zrodlo celow do komentowania.

13 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 18 | `_historia()` | — | — | `kanal._za_niedawno_u_nich`, `kanal.posty_z_kanalu`, `kanal.zapamietaj_komentarz`, `run.dzien` *(+2)* |
| 29 | `zapamietaj_komentarz(post)` | — | Odnotowuje, u kogo dzis komentowalismy. | `run.dzien`, `run.dzien.komentarze` |
| 41 | `klucz_publikacji(post)` | — | Kim jest autor posta. | `kanal._za_niedawno_u_nich`, `kanal.posty_z_kanalu`, `kanal.zapamietaj_komentarz` |
| 48 | `_wiek_minut(data)` | — | — | `kanal._za_stary`, `kanal._za_swiezy`, `run.opis_celu` |
| 58 | `_za_swiezy(post, widelki)` | — | Czy post jest na tyle swiezy, ze komentarz wygladalby jak czujka bota. | `kanal.notki_z_kanalu`, `kanal.posty_z_kanalu`, `kanal.szukaj_nowych` |
| 70 | `_za_stary(post)` | — | Cel starszy niz `config.MAKS_WIEK_CELU_DNI` — rozmowa juz sie skonczyla. | `kanal.notki_z_kanalu`, `kanal.posty_z_kanalu`, `kanal.szukaj_nowych` |
| 82 | `wartosc_celu(x)` | — | Klucz sortowania celow: WCZESNIE przed GLOSNO. | `kanal.notki_z_kanalu`, `kanal.szukaj_nowych` |
| 102 | `_za_niedawno_u_nich(post)` | — | Czy komentowalismy u tej publikacji w ostatnich dniach. | `kanal.posty_z_kanalu`, `kanal.szukaj_nowych` |
| 116 | `nasz_cel(kandydat)` | — | Czy ten cel jest NASZ — po adresie ALBO po uchwycie autora. | `kanal.posty_z_kanalu`, `kanal.szukaj_nowych` |
| 138 | `nasz_adres(url)` | — | Czy ten adres wskazuje na NASZA publikacje. | `kanal.nasz_cel` |
| 171 | `posty_z_kanalu(ile)` | WWW | Ostatnie posty z kanalu czytelnika, z liczba komentarzy i reakcji. | `run.dzien`, `run.dzien.komentarze` |
| 233 | `notki_z_kanalu(ile)` | WWW | Cudze notki, pod ktorymi mozna wejsc w dyskusje. | `personality.community_candidates`, `run.dzien`, `run.dzien.dyskusje` |
| 285 | `szukaj_nowych(ile)` | WWW | Szuka NOWYCH kont wyszukiwarka Substacka, poza naszym kregiem. | `personality.community_candidates`, `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` |

---

<a id="agent-v2konfiguracja-py"></a>
## `agent-v2/konfiguracja.py`

Wczytanie `konfiguracja.toml` i pol presetu — jeden kontrakt pol, jeden zapis.

45 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 110 | `_napis(v, gdzie)` | — | — | `konfiguracja (poziom modulu)`, `konfiguracja._dzien_tygodnia`, `konfiguracja._godzina_utc`, `konfiguracja._sciezka` *(+1)* |
| 116 | `_napis_moze_pusty(v, gdzie)` | — | Napis, ktory WOLNO zostawic pusty. | `konfiguracja (poziom modulu)`, `konfiguracja._sciezka_moze_pusta` |
| 128 | `_data_albo_pusto(v, gdzie)` | — | Dzien w postaci RRRR-MM-DD albo pusty napis znaczacy „nigdy". | `konfiguracja (poziom modulu)` |
| 154 | `_liczba(v, gdzie)` | DEAD? | — | — |
| 160 | `_kwota(v, gdzie)` | — | Kwota w USD: skonczona i nieujemna. | `konfiguracja (poziom modulu)` |
| 171 | `_calkowita_nieujemna(v, gdzie)` | — | Licznosc: ile czego. | `konfiguracja (poziom modulu)`, `konfiguracja._calkowita_dodatnia` |
| 181 | `_calkowita_dodatnia(v, gdzie)` | — | Licznosc, ktora nie ma sensu jako zero (przebiegi na dobe). | `konfiguracja (poziom modulu)` |
| 189 | `_prawda(v, gdzie)` | — | — | `konfiguracja (poziom modulu)` |
| 195 | `_strefa(v, gdzie)` | — | Nazwa strefy IANA, ktora NAPRAWDE istnieje w bazie stref. | `konfiguracja (poziom modulu)` |
| 217 | `_sekwencja_napisow(v)` | — | Lista albo krotka napisow — ale NIE sam napis. | `konfiguracja._lista_dni_tygodnia`, `konfiguracja._lista_godzin_utc`, `konfiguracja._lista_napisow`, `konfiguracja._lista_napisow_moze_pusta` *(+1)* |
| 234 | `_lista_napisow(v, gdzie)` | — | — | `konfiguracja (poziom modulu)` |
| 241 | `_lista_napisow_moze_pusta(v, gdzie)` | — | Lista napisow, w ktorej PUSTA jest poprawna odpowiedzia. | `konfiguracja (poziom modulu)`, `konfiguracja._lista_domen` |
| 257 | `_widelki(v, gdzie)` | — | Zakres [od, do] nieujemnych liczb calkowitych. | `konfiguracja (poziom modulu)`, `konfiguracja._godziny` |
| 275 | `_godziny(v, gdzie)` | — | Para godzin doby [od, do] w zakresie 0-24. | `konfiguracja (poziom modulu)` |
| 283 | `_godzina_utc(v, gdzie)` | — | Godzina zegara `HH:MM` w UTC — postac, ktora rozumie `OnCalendar=`. | `konfiguracja (poziom modulu)`, `konfiguracja._lista_godzin_utc` |
| 292 | `_lista_godzin_utc(v, gdzie)` | — | Niepusta lista godzin `HH:MM` bez powtorzen, w kolejnosci doby. | `konfiguracja (poziom modulu)` |
| 303 | `_dzien_tygodnia(v, gdzie)` | — | — | `konfiguracja._lista_dni_tygodnia` |
| 316 | `_lista_dni_tygodnia(v, gdzie)` | — | Lista dni tygodnia; pusta znaczy „bez artykulow". | `konfiguracja (poziom modulu)` |
| 328 | `_lista_dni_miesiaca(v, gdzie)` | — | Days 1..28 exist in every month; duplicates are configuration errors. | `konfiguracja (poziom modulu)` |
| 337 | `_sciezka(v, gdzie)` | — | Sciezka do pliku wzgledem korzenia repozytorium (albo bezwzgledna). | `konfiguracja (poziom modulu)` |
| 347 | `_sciezka_moze_pusta(v, gdzie)` | — | — | `konfiguracja (poziom modulu)` |
| 352 | `_slownik_list(v, gdzie)` | — | Tablica `klucz = [napisy]`. | `konfiguracja (poziom modulu)` |
| 376 | `_slownik_napisow(v, gdzie)` | — | — | `konfiguracja (poziom modulu)`, `konfiguracja._slownik_adresow`, `konfiguracja._slownik_miesiecy` |
| 384 | `_slownik_adresow(v, gdzie)` | — | Nazwa -> adres kanalu RSS/Atom. | `konfiguracja (poziom modulu)` |
| 396 | `_lista_domen(v, gdzie)` | — | Lista hostow (bez schematu i sciezki), pusta dozwolona. | `konfiguracja (poziom modulu)` |
| 409 | `_slownik_miesiecy(v, gdzie)` | — | Tablica `"1".."12" = napis` (klucze TOML sa napisami). | `konfiguracja (poziom modulu)` |
| 590 | `sciezka(agent_dir)` | DEAD? | — | — |
| 594 | `splaszcz(dane, nazwa)` | — | `{"temat": {"nisza": ...}}` na `{"temat.nisza": ...}` — jeden poziom. | `konfiguracja.wczytaj_tekst`, `preset.wczytaj_tekst` |
| 607 | `sprawdz_plaskie(plaskie, nazwa)` | — | Nieznane pole to blad; kazde znane przechodzi przez swoj walidator. | `konfiguracja.wczytaj_tekst`, `preset.wczytaj_tekst` |
| 623 | `wczytaj_tekst(tekst, nazwa)` | — | Surowy TOML (napis) -> zwalidowane pola plaskie. | `konfiguracja.wczytaj` |
| 641 | `wczytaj(plik)` | DEAD? | Surowa zawartosc pliku, sprawdzona co do ksztaltu. | — |
| 651 | `zdjecie(cfg)` | DEAD? | Kopia stalych konta z modulu `config`, do pozniejszego przywrocenia. | — |
| 660 | `przywroc(cfg, zdj)` | — | Przywraca stan ze `zdjecie`. | `preset.proba_konfiguracji`, `preset.zastosuj` |
| 675 | `_rozloz_godziny(ile, baza)` | — | Godziny zegara dla `ile` przebiegow, gdy preset podal tylko liczbe. | `konfiguracja._plan` |
| 704 | `konto_ze_srodowiska(cfg, srodowisko)` | — | Nadpisuje uchwyt i marke wartosciami ze srodowiska. | `preset.rozwiaz` |
| 715 | `uchwyt_konta(pola, srodowisko)` | — | Uchwyt, ktory NAPRAWDE bedzie uzyty: ze srodowiska, a gdy go tam nie ma — z presetu. | `preset.podlacz` |
| 721 | `placeholder_konta(uchwyt, marka)` | — | Co w koncie jest jeszcze placeholderem (pusta lista = konto gotowe). | `alarm.konto_placeholder`, `preset.sprawdz` |
| 738 | `_sciezka_w_repo(cfg, napis)` | — | Bezwzgledna jak jest; `repo:x` i zwykla wzgledna — od korzenia repozytorium. | `konfiguracja._plan` |
| 748 | `_plan(dane, cfg)` | — | Co przestawic — policzone W CALOSCI, zanim cokolwiek zostanie zapisane. | `konfiguracja.zastosuj` |
| 936 | `zastosuj(dane, cfg)` | — | Wklada wartosci do modulu `config`. | `preset.rozwiaz`, `preset.zastosuj` |
| 962 | `on_calendar_agenta(godziny)` | DEAD? | Zegar rutyny dnia: jedna linia na godzine UTC. | — |
| 967 | `on_calendar_artykulu(dni, godzina, ile, dni_miesiaca)` | DEAD? | Zegar artykulu; pusta lista, gdy artykulow nie ma. | — |
| 979 | `_toml_napis(v)` | — | Napis w cudzyslowie z ucieczkami. | `konfiguracja.toml_wartosc` |
| 986 | `toml_wartosc(v)` | — | — | `konfiguracja.zapisz_toml`, `preset.z_konfiguracji` |
| 1005 | `zapisz_toml(dane, naglowek, sekcje_dodatkowe)` | — | Pola plaskie -> tekst TOML. | `preset.eksportuj` |

---

<a id="agent-v2kopia-subskrybentow-py"></a>
## `agent-v2/kopia_subskrybentow.py`

Kopia listy subskrybentow — jedyne aktywo, ktorego nie da sie odtworzyc.

4 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 72 | `_wierszy(tekst)` | — | — | `kopia_subskrybentow.main` |
| 76 | `_to_lista_subskrybentow(tekst)` | — | Czy to naprawde eksport listy, a nie przypadkowy plik albo strona HTML. | `kopia_subskrybentow.main` |
| 88 | `pobierz_z_panelu()` | WWW | Sciaga liste z wlasnego panelu i zapisuje ja jako CSV do `przychodzace/`. | `kopia_subskrybentow.main` |
| 133 | `main()` | — | — | `kopia_subskrybentow (poziom modulu)`, `run.dzien`, `run.dzien.kopia_listy` |

---

<a id="agent-v2korpus-kanalow-py"></a>
## `agent-v2/korpus_kanalow.py`

Tematy z kanalow, ktore robia dokladnie to, co ma robic nasza publikacja.

14 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 105 | `oczysc(tytul)` | — | Zdejmuje obietnice, zostawia zdarzenie. | `korpus_kanalow._kandydaci` |
| 118 | `_kandydaci(pozycje)` | — | (kanal, surowy tytul, data RRRR-MM-DD, url, skrot) -> kandydaci. | `korpus_kanalow.przetworz`, `korpus_kanalow.wpisy_z_kanalu` |
| 156 | `przetworz(wpisy)` | — | (nazwa_kanalu, element Atom z YouTube) -> kandydaci. | `korpus_kanalow.korpus_kanalow` |
| 173 | `_tekst(el)` | — | — | `korpus_kanalow.wpisy_z_kanalu` |
| 216 | `_bez_wstepu(tekst)` | — | Opis bez reklamy i naglowka redakcji z POCZATKU. | `korpus_kanalow._skrot` |
| 255 | `_skrot(*elementy)` | — | Pierwszy niepusty opis wpisu, bez HTML-a, przyciety do `SKROT_ZNAKOW`. | `korpus_kanalow.wpisy_z_kanalu` |
| 283 | `_data_rss(napis)` | — | `pubDate` RSS (RFC 2822) albo data ISO -> RRRR-MM-DD; pusto, gdy nie da sie. | `korpus_kanalow.wpisy_z_kanalu`, `stages.zaczyn_z_kanalow` |
| 303 | `wpisy_z_kanalu(nazwa, tresc)` | — | Kanal RSS 2.0 albo Atom (blog laboratorium, lista publikacji) -> kandydaci. | `korpus_kanalow.korpus_kanalow` |
| 359 | `przeplot_zrodel(po_zrodlach)` | — | Po jednym wpisie z kazdego zrodla na zmiane, od najswiezszych. | `korpus_kanalow.korpus_kanalow` |
| 405 | `_rdzen(temat)` | — | Slowa nosne tytulu — do porownywania, czy dwa kanaly mowia o tym samym. | `korpus_kanalow.wielkie_wydarzenia` |
| 417 | `_numer_wersji(slowo)` | — | Czy token wyglada na numer wydania: ma cyfre i nie jest rokiem. | `korpus_kanalow.wielkie_wydarzenia` |
| 425 | `wielkie_wydarzenia(korpus, min_kanalow, min_wspolnych, swiezosc_dni, min_kanalow_premiery)` | — | Rzeczy, o ktorych mowi NARAZ kilka roznych kanalow. | `audyt_tematow.main`, `stages.znajdz_ciekawostki` |
| 576 | `_cache_key()` | — | — | `korpus_kanalow.korpus_kanalow` |
| 582 | `korpus_kanalow(ile)` | — | — | `audyt_tematow.main`, `korpus_kanalow (poziom modulu)`, `stages.zaczyn_z_kanalow`, `stages.znajdz_ciekawostki` |

---

<a id="agent-v2llm-py"></a>
## `agent-v2/llm.py`

Provider calls with per-attempt accounting, reservations and deadlines.

26 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 54 | `_dostawca(model)` | — | Czyj to model. | `llm._cost`, `llm._preflight`, `llm._reserve_attempt`, `llm.call` *(+1)* |
| 72 | `_preflight(purpose, conn, run_id)` | DB | Warunki, które decydują, czy wywołanie może się w ogóle udać. | `llm._deepseek_pick_from_urls`, `llm._reserve_attempt`, `llm.call`, `llm.obraz` |
| 199 | `_narzedzie_wyszukiwania(model)` | — | Nazwa narzedzia wyszukiwania; ostrzega RAZ NA PROCES o braku wpisu. | `llm._call_claude` |
| 208 | `_cost(model, tokens_in, tokens_out, web_searches, cache_hit, when, cache_write_5m, cache_write_1h)` | — | — | `llm._settle_attempt` |
| 224 | `_log(purpose, model, tin, tout, searches, usd, verified)` | — | — | `llm.call` |
| 235 | `_call_claude(purpose, system, user, web_search)` | — | — | `llm.call`, `llm.call.transport` |
| 316 | `_call_deepseek_responses(purpose, system, user)` | — | DeepSeek przez /responses z server-side `web_search`. | `llm.call`, `llm.call.transport` |
| 419 | `_call_deepseek_responses.walk(node)` | — | — | `llm._call_deepseek_responses` |
| 453 | `_call_openai_responses(purpose, system, user)` | — | OpenAI przez `/responses`. | `llm.call`, `llm.call.transport` |
| 546 | `_call_openai_responses.zbierz(node)` | — | — | `llm._call_openai_responses` |
| 563 | `_deepseek_pick_from_urls(purpose, system, user, urls, conn, run_id, partial)` | — | Reconstruct a search result with the ordinary streamed, billed transport. | `llm.call` |
| 591 | `_read_search_sources(urls)` | — | Recover evidence from already-found public URLs, without another search. | `llm._deepseek_pick_from_urls` |
| 603 | `_read_search_sources.public_url(url)` | — | — | `llm._read_search_sources` |
| 664 | `_call_deepseek(purpose, system, user)` | — | — | `llm.call`, `llm.call.transport` |
| 755 | `przejsciowy(exc)` | — | Czy ten błąd ma szansę minąć sam. | `llm.call` |
| 802 | `_reserve_attempt(conn, run_id, purpose, system, user, web_search, operation, attempt_no, max_tokens)` | DB | — | `llm.call`, `llm.obraz` |
| 844 | `_settle_attempt(conn, call_id, state, model, started, ok, exc)` | DB | — | `llm.call` |
| 860 | `image_output_price()` | — | — | `llm._reserve_attempt`, `llm._settle_image` |
| 869 | `call(purpose, system, user, conn, run_id, web_search, collect_urls, max_tokens, thinking)` | — | — | `aktualne_modele.pobierz`, `artykul_z_puli.temat_z_faktu`, `llm._deepseek_pick_from_urls`, `llm.ratuj_json` *(+25)* |
| 905 | `call.transport()` | — | — | `llm.call` |
| 966 | `obraz(opis, conn, run_id)` | — | — | `stages.grafika` |
| 978 | `obraz.request()` | — | — | `llm.obraz` |
| 998 | `_settle_image(conn, call_id, data, ok, error)` | DB | — | `llm.obraz` |
| 1014 | `_obiekty_json(tekst)` | — | Kolejne ZBILANSOWANE obiekty JSON w tekscie, od lewej. | `llm.parse_json` |
| 1079 | `ratuj_json(purpose, tekst, ksztalt, conn, run_id)` | — | Drugie podejście do odpowiedzi, która nie zawierała JSON-a. | `stages.discovery`, `stages.znajdz_ciekawostki`, `stages.zweryfikuj` |
| 1124 | `parse_json(text)` | — | Wyciąga obiekt JSON z odpowiedzi modelu. | `aktualne_modele.pobierz`, `artykul_z_puli.temat_z_faktu`, `llm.call`, `personality.short_form` *(+24)* |

---

<a id="agent-v2migracja-okno-promocji-py"></a>
## `agent-v2/migracja_okno_promocji.py`

Jednorazowe uzupelnienie pola `dodane` w kolejce promocji.

2 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 50 | `daty_publikacji()` | — | Tytul artykulu -> data pierwszej udanej publikacji (YYYY-MM-DD). | `migracja_okno_promocji.main` |
| 78 | `main()` | — | — | `migracja_okno_promocji (poziom modulu)` |

---

<a id="agent-v2norma-py"></a>
## `agent-v2/norma.py`

Ile agent naprawde zrobil, dzien po dniu, wobec normy.

16 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 260 | `budzety_dzienne()` | — | Ile agent SOBIE ZALOZYL kazdego dnia — z pliku, nie z dzisiejszej konfiguracji. | `norma.main` |
| 308 | `_data(dzien)` | — | „2026-08-30" -> datetime w UTC. | `norma._poprawna_data`, `norma.dni_okna`, `norma.main` |
| 313 | `_poprawna_data(dzien)` | — | Czy da sie z tego zrobic date. | `norma.budzety_dzienne`, `norma.slad_dziennika`, `norma.wczytaj` |
| 330 | `wczytaj(dni)` | — | (zrobione, nieudane) — liczniki per dzien i rodzaj. | `norma.main` |
| 355 | `slad_dziennika(zalozone)` | — | (najstarszy znany dzien, zbior dni z JAKIMKOLWIEK wpisem w dzienniku). | `norma.main` |
| 401 | `_znak(ile, norma)` | — | Jak daleko od planu NA TEN DZIEN. | `norma._komorka`, `norma.main` |
| 440 | `dni_okna(dni, z_wpisami, zalozone, najstarszy)` | — | Wszystkie dni okna — TAKZE te, w ktorych nie wyszlo NIC. | `norma.main` |
| 485 | `_komorka(ile, cel, wyciszony, ma_wpisy, w_toku, szacowany)` | — | Jedna kratka tabeli. | `norma.main` |
| 510 | `przebiegow_dzis()` | DB | Ile przebiegow agenta domknelo sie dzis. | `norma.main` |
| 525 | `godziny_przebiegow()` | — | Minuty od polnocy UTC, o ktorych systemd odpala agenta. | `norma.przebiegow_naleznych` |
| 559 | `przebiegow_naleznych(teraz)` | — | (ile przebiegow POWINNO juz oddac swoja czesc, ile ich jest na dobe). | `norma.main` |
| 589 | `slad(dni)` | — | Gdzie dokladnie psuja sie publikacje — wg pozycji w serii i odstepu. | `norma.main` |
| 683 | `main()` | — | — | `norma (poziom modulu)` |
| 993 | `main._srednia(r)` | — | None, gdy tej pozycji nie zmierzylismy ANI RAZU. | `norma.main`, `norma.main._procent_normy` |
| 1004 | `main._wykonanie(r)` | — | Ile z tego, co agent SOBIE ZALOZYL, naprawde zrobil. | `norma.main` |
| 1008 | `main._procent_normy(r)` | — | — | `norma.main` |

---

<a id="agent-v2personality-py"></a>
## `agent-v2/personality.py`

Opt-in conversational short forms.

23 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 26 | `_injection(text)` | — | Reject explicit role replacement; ordinary links in source posts are data. | `personality._valid`, `personality.short_form`, `personality.targets`, `stages.przygotuj_artykul_do_publikacji` *(+2)* |
| 31 | `_date(value)` | — | — | `personality.notes`, `personality.statistics` |
| 39 | `_rows(name)` | — | Read bounded local history; an incomplete final JSONL line is harmless. | `personality.memory`, `personality.memory_state`, `personality.statistics` |
| 62 | `memory()` | — | — | `personality._swiat`, `personality.notes`, `personality.remember`, `personality.short_form` *(+1)* |
| 66 | `memory_state()` | — | Keep milestones after individual Notes leave the bounded prompt memory. | `personality.notes`, `personality.remember` |
| 87 | `_count(value)` | — | — | `personality.small_account`, `personality.statistics` |
| 91 | `statistics(now)` | — | Publishable facts only: net growth and cumulative measured Note views. | `personality.notes` |
| 138 | `statistics.handles(row)` | — | — | `personality.statistics` |
| 163 | `voice_blocks(kind)` | — | The same identity and voice, in the same order, for every writing role. | `personality._system`, `stages.system_pisarza` |
| 171 | `_system(kind)` | — | System krotkiej formy: tozsamosc, styl, GLOS WSPOLNY, potem glos formy. | `personality.short_form` |
| 207 | `_rozdziel_rubryke(temat)` | — | „NAZWA: polecenie" -> („NAZWA", „polecenie"). | `personality._etykiety`, `personality.notes` |
| 226 | `_etykiety()` | — | Nazwy wszystkich rubryk presetu — do sprawdzenia, czy nie wyciekly. | `personality._valid` |
| 231 | `_valid(text, maximum)` | — | — | `personality.short_form` |
| 247 | `short_form(conn, run_id, kind, material)` | **$**((zmienna)) | One paid decision: respond, or remain silent. | `personality.interaction`, `personality.notes` |
| 311 | `short_form.finish(output, reason)` | — | — | `personality.short_form` |
| 362 | `_swiat(conn, run_id)` | — | Co sie w tej branzy WYDARZYLO — naglowki z datami, jako tlo notki. | `personality.notes` |
| 423 | `notes(conn, run_id, ile, od)` | — | Choose a subject from the persona, not the research bank. | `stages.notki_dnia` |
| 472 | `interaction(conn, run_id, kind, post)` | — | Adapt persona JSON to the existing browser publication contracts. | `stages.comment_on`, `stages.ocen_restack`, `stages.reply_to` |
| 484 | `targets(posts)` | — | Free topical prefilter. | `personality.community_candidates`, `stages.wybierz_cele` |
| 494 | `community_candidates()` | — | Relevant new people need not have received a comment first. | `run.dzien`, `run.dzien.nowi_dla_persony` |
| 516 | `small_account(profile, maximum)` | — | Unknown size is not evidence of a small account. | `browser._klik_na_profilu`, `browser.konto_za_duze` |
| 524 | `remember(note, publication)` | — | Commit once, only after the browser confirms a new publication. | `personality.remember_interaction`, `run.dzien`, `run.dzien.notki` |
| 559 | `remember_interaction(kind, candidate, publication, target)` | — | Only confirmed persona output becomes autobiographical continuity. | `browser.restackuj_w_kanale`, `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` *(+1)* |

---

<a id="agent-v2preset-py"></a>
## `agent-v2/preset.py`

Preset: kartridz z CALA redakcja, podlaczany i odlaczany jednym poleceniem.

40 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 187 | `korzen(agent_dir)` | — | — | `preset.aktywacja`, `preset.katalog_presetow`, `preset.odlacz`, `preset.podlacz` |
| 191 | `katalog_presetow(agent_dir)` | — | — | `preset.lista` |
| 195 | `katalog_instancji(agent_dir)` | — | — | `preset.aktywacja`, `preset.podlacz` |
| 199 | `wskaznik(agent_dir)` | — | — | `preset.czytaj_wskaznik`, `preset.odlacz`, `preset.podlacz` |
| 203 | `_wzgledna(p, baza)` | — | Sciezka wzgledem `baza` (posix), a gdy lezy poza nia — bezwzgledna. | `preset.podlacz` |
| 211 | `_bezwzgledna(napis, baza)` | — | — | `preset.aktywacja`, `preset.odlacz` |
| 216 | `plik_presetu(sciezka)` | — | Katalog presetu -> jego `preset.toml`; plik -> ten plik. | `preset.wczytaj`, `preset.znajdz` |
| 225 | `_kanoniczne(x)` | — | — | `preset.odcisk`, `preset.pochodzenie` |
| 235 | `odcisk(pola, schema, bloki, zasoby)` | — | SHA-256 pol, blokow I ZASOBOW STYLU. | `preset.wczytaj_tekst` |
| 255 | `_wczytaj_bloki(katalog)` | — | `prompty/<blok>.md` z katalogu presetu; tylko znane nazwy, tylko niepuste. | `preset.wczytaj_tekst` |
| 289 | `_rozwiaz_sciezki(pola, katalog)` | — | Sciezki stylu wzgledem KATALOGU PRESETU, gdy tam leza; inaczej wzgledem repo. | `preset.wczytaj_tekst` |
| 309 | `_zasoby_kartridza(pola, katalog)` | — | Skroty plikow stylu lezacych W KATALOGU presetu: {sciezka wzgledna: sha256}. | `preset.wczytaj_tekst` |
| 334 | `wczytaj_tekst(tekst, nazwa_pliku, plik, katalog)` | — | Tekst TOML presetu -> `Preset`. | `preset.wczytaj` |
| 391 | `wczytaj(sciezka)` | — | Preset z katalogu (`presety/<nazwa>/`) albo z pojedynczego pliku. | `preset.aktywacja`, `preset.podlacz` |
| 403 | `proba_konfiguracji(cfg, baza)` | — | Kopia stalych `config` do bezpiecznego przymierzenia presetu. | `preset.rozwiaz` |
| 429 | `rozwiaz(preset, cfg, baza, srodowisko)` | — | Preset przymierzony na kopii: (kopia po zastosowaniu, meldunki). | `preset.pochodzenie`, `preset.sprawdz` |
| 450 | `_bez_domyslnego_korpusu(preset, cfg)` | — | Pusty `styl.korpus` w kartridzu znaczy BRAK korpusu, nie „ten z katalogu silnika". | `preset.rozwiaz`, `preset.zastosuj` |
| 464 | `pochodzenie(preset, cfg, baza)` | DEAD? | Skad kazda stala konta bierze wartosc: „preset" albo „silnik". | — |
| 487 | `_dostawcy_tekstu()` | — | Lista z `llm`, zeby walidator nie mial wlasnej, rozjezdzajacej sie kopii. | `preset.sprawdz` |
| 496 | `_dostawca(model)` | — | Dostawca po prefiksie — TA SAMA regula co `llm._dostawca`. | `preset.sprawdz` |
| 515 | `_napisy(x)` | — | Wszystkie napisy w zagniezdzonej wartosci. | `preset.sprawdz` |
| 527 | `sprawdz(preset, cfg, baza, srodowisko, do_aktywacji)` | — | Reguly PONAD ksztaltem pol. | `preset.podlacz` |
| 727 | `zastosuj(preset, cfg, baza)` | DEAD? | Neutralna baza, potem pola i bloki presetu. | — |
| 749 | `_zapisz_atomowo(plik, tekst)` | — | — | `personality.remember`, `personality.short_form`, `personality.short_form.finish`, `preset._sprawdz_wlasciciela` *(+1)* |
| 764 | `_teraz()` | — | — | `preset._dopisz_do_dziennika`, `preset.podlacz`, `preset.z_konfiguracji` |
| 768 | `_dopisz_do_dziennika(katalog, wpis)` | — | Dziennik aktywacji instancji; oddaje numer TEJ aktywacji. | `preset._sprawdz_wlasciciela`, `preset.odlacz`, `preset.podlacz` |
| 784 | `czytaj_wskaznik(agent_dir)` | — | Surowa tresc wskaznika (bez wczytywania presetu) albo None. | `preset.aktywacja`, `preset.aktywacja_nadal_wazna` |
| 799 | `aktywacja(agent_dir, srodowisko)` | DEAD? | Co jest podlaczone. | — |
| 834 | `podlacz(sciezka, agent_dir, cfg, baza, instancja, srodowisko, przejmij)` | DEAD? | Sprawdza preset W CALOSCI i dopiero potem atomowo przelacza wskaznik. | — |
| 878 | `wlasciciel(katalog)` | — | Manifest wlasciciela katalogu instancji albo None, gdy katalog jest nowy. | `preset._sprawdz_wlasciciela` |
| 890 | `_sprawdz_wlasciciela(katalog, preset, przejmij, uchwyt)` | — | Instancja nalezy do JEDNEJ redakcji: tego presetu i tego konta. | `preset.podlacz` |
| 928 | `odlacz(agent_dir)` | DEAD? | Usuwa wskaznik. | — |
| 968 | `wymagaj_aktywnego(cfg, co)` | — | Brama na wejsciu `run.py` i `artykul_z_puli.py`: bez presetu nie ma pracy. | `artykul_z_puli.main`, `run.main` |
| 989 | `tylko_podglad(cfg)` | DEAD? | Aktywacja ze zmiennej AGENT_V2_PRESET to podglad: bez platnych wywolan i publikacji. | — |
| 1002 | `aktywacja_nadal_wazna(cfg)` | — | Pusty napis, gdy aktywacja z pamieci procesu nadal stoi we wskazniku; inaczej powod. | `preset.wymagaj_aktywnego` |
| 1038 | `lista(agent_dir)` | — | Presety w `presety/`: katalogi z `preset.toml` i pojedyncze pliki `.toml`. | `preset.znajdz` |
| 1053 | `nazwa_z_pliku(plik)` | — | Nazwa presetu z jego polozenia: katalog albo nazwa pliku. | `preset.znajdz` |
| 1059 | `znajdz(nazwa, agent_dir)` | DEAD? | Preset po nazwie (katalog przed plikiem) albo po sciezce. | — |
| 1072 | `z_konfiguracji(tekst_toml, nazwa, opis)` | DEAD? | Stary `konfiguracja.toml` -> tekst presetu (naglowek + oryginal, z komentarzami). | — |
| 1096 | `eksportuj(preset)` | DEAD? | Preset w postaci znormalizowanej (te same pola, ten sam odcisk po wczytaniu). | — |

---

<a id="agent-v2raport-statystyk-py"></a>
## `agent-v2/raport_statystyk.py`

Co przyniosla kazda notka, restack i artykul — do czytania przez czlowieka.

5 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 28 | `_skrot(tekst, ile)` | — | — | `raport_statystyk.main` |
| 54 | `_mediana(liczby)` | — | — | `raport_statystyk.dwie_epoki` |
| 62 | `dwie_epoki(najnowsze)` | — | Epoka SPRZED zmiany tematu osobno, epoka PO niej osobno. | `raport_statystyk.main` |
| 162 | `wzrost_konta()` | — | Ilu nas czyta i czy tego przybywa. | `raport_statystyk.main` |
| 220 | `main()` | — | — | `raport_statystyk (poziom modulu)` |

---

<a id="agent-v2research-tasks-py"></a>
## `agent-v2/research_tasks.py`

Record article evidence gaps and target an existing second search at them.

3 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 10 | `decision(directory, run_id, stage, **details)` | — | Operational trace only. | `artykul_z_puli._przebieg`, `artykul_z_puli.wybierz_fakt`, `stages.zaczyn_z_kanalow` |
| 22 | `snapshot(directory, run_id, brief, corpus, missing)` | — | Keep exact source URLs and short excerpts, separate from confirmed evidence. | `artykul_z_puli._przebieg`, `research_tasks.followup` |
| 43 | `followup(directory, run_id, brief, corpus, min_sources, min_primary)` | — | Refine the already-budgeted retry, without adding an LLM call or a loop. | `artykul_z_puli._przebieg` |

---

<a id="agent-v2result-cache-py"></a>
## `agent-v2/result_cache.py`

Content-addressed cache.

5 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 10 | `digest(value)` | — | — | `result_cache.code_fingerprint`, `retry_policy.path_for`, `run.cached`, `stages.zweryfikuj` |
| 15 | `read(path, max_age)` | — | — | `retry_policy.remaining`, `run.cached`, `stages.zweryfikuj` |
| 24 | `write(path, value)` | — | — | `retry_policy.defer`, `run.cached`, `stages.napraw_obalone`, `stages.zweryfikuj` |
| 28 | `write_json(path, value)` | — | Replace a JSON document atomically, keeping the prior file on failure. | `aktualne_modele.pobierz`, `feed_cache.fetch`, `research_tasks.snapshot`, `result_cache.write` |
| 41 | `code_fingerprint(root)` | — | — | `run.cached` |

---

<a id="agent-v2retry-policy-py"></a>
## `agent-v2/retry_policy.py`

Remember server-requested pauses without treating a deferred call as an attempt.

4 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 10 | `retry_after(headers, now)` | — | Retry-After can be seconds or an HTTP date; malformed values are ignored. | `feed_cache.fetch`, `llm.call`, `stages.fetch` |
| 29 | `path_for(directory, scope)` | — | — | `aktualne_modele.pobierz`, `llm.call`, `stages.fetch` |
| 33 | `remaining(path)` | — | — | `aktualne_modele.pobierz`, `llm.call`, `retry_policy.defer`, `stages.fetch` |
| 44 | `defer(path, seconds)` | — | — | `aktualne_modele.pobierz`, `llm.call`, `stages.fetch` |

---

<a id="agent-v2run-py"></a>
## `agent-v2/run.py`

Jedno polecenie uruchamiające — to samo lokalnie i na serwerze.

**Wejscie produkcyjne:** `nia-agent.timer`, piec razy na dobe: `run.py --dzien --wyslij`

41 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 60 | `_utf8_stdout()` | — | Konsola Windows domyślnie cp1252 i wywala się na polskich znakach. | `run.main` |
| 76 | `cached(stage, produce, use_cache)` | — | — | `run.main` |
| 108 | `odmow_publikacji_z_kopii(wyslij)` | — | Kopia testowa nie ma prawa nic opublikowac. | `run.main` |
| 126 | `zajmij_zamek()` | — | Nie pozwala dwóm przebiegom działać naraz. | `run.main` |
| 161 | `opis_celu(cel)` | — | Co wiedzielismy o celu w chwili pisania — do dziennika. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` |
| 184 | `zostal_czas(na_co, potrzeba_s)` | — | Czy zdazymy jeszcze cokolwiek zrobic przed koncem czasu przebiegu. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze`, `run.dzien.notki` *(+4)* |
| 244 | `_pod_rzad_w_bloku(co, na_co)` | — | Ile porazek pod rzad naliczyl TEN blok, odkad sie zaczal. | `run.rytm` |
| 267 | `rytm(co, na_co, stan)` | — | Przerwa MIEDZY dwoma dzialaniami tego samego rodzaju. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze`, `run.dzien.notki` *(+3)* |
| 326 | `zmiesci_sie(rodzaj, ile, udzial)` | — | Ile z zaplanowanych dzialan NAPRAWDE zmiesci sie w czasie przebiegu. | `run.dzien` |
| 348 | `zmiesci_sie.potrzeba(n)` | — | — | `run.zmiesci_sie` |
| 361 | `ile_przebiegow_zostalo(conn)` | DB | Ile przebiegow dnia jeszcze bedzie, wliczajac biezacy. | `run.dzien` |
| 437 | `_po_zmianie_tematu(kiedy)` | — | Czy ten wpis jest z obecnej epoki konta. | `run.cele_wedlug_pierwszenstwa` |
| 516 | `_slug(tekst)` | — | Nazwa do porownywania: same litery i cyfry ASCII, malymi. | `run._reakcje_z_dziennika`, `run._slug_hosta` |
| 529 | `_slug_hosta(host)` | — | Pierwszy czlon adresu jako slug: `www.imienazwisko.com` -> `imienazwisko`. | `run.cele_wedlug_pierwszenstwa` |
| 537 | `_reakcje_z_dziennika()` | — | Jeden przebieg po dzienniku, dwie odpowiedzi o tych samych ludziach. | `run.kogo_juz_dotknelismy`, `run.reagujacy_jako_cele` |
| 631 | `kogo_juz_dotknelismy()` | — | Slugi nazw ludzi, ktorzy zareagowali na NASZA tresc — z dziennika. | `run.cele_wedlug_pierwszenstwa` |
| 655 | `nasi_czytelnicy()` | — | Uchwyty ludzi, ktorzy JUZ nas czytaja — z `czytelnicy.jsonl`. | `run.reagujacy_jako_cele` |
| 703 | `reagujacy_jako_cele()` | — | Ludzie, ktorzy zareagowali na nasza tresc, jako CELE WPROST. | `run.cele_wedlug_pierwszenstwa` |
| 786 | `_przeplot(pierwsza, druga)` | — | Na przemian z dwoch list; gdy jedna sie konczy, druga idzie dalej. | `run.cele_wedlug_pierwszenstwa` |
| 802 | `cele_wedlug_pierwszenstwa(historia)` | — | Hosty do zaczepienia, w kolejnosci pierwszenstwa. | `run.dzien`, `run.dzien.obserwuj`, `run.dzien.subskrybuj` |
| 911 | `powod_pustej_puli(rachunek)` | — | Zdanie do dziennika, gdy po odsianiu nie zostal nikt. | `run.dzien`, `run.dzien.obserwuj`, `run.dzien.subskrybuj` |
| 940 | `kogo_juz_subskrybujemy()` | — | Uchwyty, na ktore subskrypcja NIE MA JUZ CO wysylac. | `run.dzien`, `run.dzien.subskrybuj` |
| 1002 | `czy_juz_subskrybujemy(host, zamkniete, pamiec)` | — | Czy ten HOST wskazuje konto, na ktore nie ma juz po co wchodzic. | `run.dzien`, `run.dzien.subskrybuj` |
| 1027 | `dzien(conn, run_id, wyslij)` | WWW | Jeden dzień pracy konta: notki, komentarze, odpowiedzi, polubienia. | `run.main` |
| 1145 | `dzien.blok(nazwa, robota)` | — | — | `run.dzien` |
| 1178 | `dzien.odpowiedzi()` | WWW | — | `run.dzien` |
| 1279 | `dzien.notki()` | WWW | — | `run.dzien`, `run.dzien.dyskusje` |
| 1405 | `dzien.komentarze()` | WWW | — | `run.dzien` |
| 1659 | `dzien.dyskusje()` | WWW | Wejscie w rozmowe pod cudza notka. | `run.dzien` |
| 1761 | `dzien.nowi_dla_persony()` | — | — | `run.dzien`, `run.dzien.obserwuj`, `run.dzien.subskrybuj` |
| 1768 | `dzien.obserwuj()` | WWW | Obserwuje autorów, których teksty faktycznie czytaliśmy. | `run.dzien` |
| 2006 | `dzien.subskrybuj()` | WWW | Subskrybuje publikacje, ktore naprawde czytamy — i pilnuje dubli. | `run.dzien` |
| 2188 | `dzien.polubienia()` | WWW | — | `run.dzien` |
| 2195 | `dzien.restacki()` | WWW | Podanie dalej trafia do kanału NASZYCH obserwujących i powiadamia autora oryginału — za cenę jednego zdania zamiast całej notki. | `run.dzien` |
| 2230 | `dzien.zalegly_artykul()` | — | Dowozi tekst, ktory zostal na dysku po nieudanej publikacji. | `run.dzien` |
| 2295 | `dzien.kopia_listy()` | — | Jedyne aktywo, ktorego nie da sie odtworzyc — i jedyne miejsce, gdzie wlasciciel musial dotad cos kliknac. | `run.dzien` |
| 2344 | `_sygnal_ma_zostawic_slad()` | — | Zamienia SIGTERM na wyjatek, zeby przebieg zdazyl sie zapisac. | `run.main` |
| 2360 | `_sygnal_ma_zostawic_slad.podnies(numer, _ramka)` | — | — | `run._sygnal_ma_zostawic_slad` |
| 2370 | `main()` | WWW DB | — | `run (poziom modulu)` |
| 2976 | `_done(conn, run_id, stage)` | DB | — | `run.main` |
| 2982 | `_summary(conn, run_id)` | DB | — | `run._done`, `run.main` |

---

<a id="agent-v2stages-py"></a>
## `agent-v2/stages.py`

Etapy lancucha, po kolei, w pamieci.

176 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 76 | `_na_kanal(nazwa)` | DB | Wszystko, co ta funkcja zaplaci, ksieguje sie na kanal `nazwa`. | `artykul_z_puli.main`, `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` *(+16)* |
| 106 | `_na_kanal.zewnetrzny(f)` | DB | — | `stages._na_kanal` |
| 114 | `_na_kanal.zewnetrzny.wewnetrzny(*a, **k)` | DB | — | `stages._na_kanal.zewnetrzny` |
| 191 | `_blok_stylu()` | — | Opis glosu z presetu — albo jawne „bez uwag", zeby sekcja nie byla pusta. | `stages._pola_wspolne` |
| 235 | `_blok_presetu(nazwa)` | — | Blok `prompty/<nazwa>.md` z presetu — albo jego zdanie zastepcze. | `artykul_z_puli.temat_z_faktu`, `stages._pola_wspolne` |
| 242 | `_blok_domen()` | — | Hosty dokumentow pierwotnych z presetu, jako jedna linia dla dyskoverii. | `stages._pola_wspolne` |
| 248 | `_blok_przykladow(klucz, gdy_pusto)` | — | Przyklady z niszy jako lista punktow — albo polecenie, gdy ich nie ma. | `stages._pola_wspolne` |
| 275 | `_blok_po_ludzku()` | — | Wspolny blok „nie brzmij jak maszyna" — JEDNO zrodlo, nie cztery kopie. | `stages._pola_wspolne` |
| 302 | `_blok_po_ludzku._dolacz()` | — | — | `stages._blok_po_ludzku` |
| 316 | `_pola_wspolne()` | — | Nisza, marka i jezyk — czytane z configu przy KAZDYM wywolaniu. | `stages._prompt` |
| 378 | `_prompt(name, **fields)` | — | — | `stages.bibliotekarz`, `stages.classify`, `stages.comment_on`, `stages.discovery` *(+18)* |
| 385 | `recent_angles(conn, limit)` | DB | Ostatnie kąty redakcyjne — wejście do reguły różnorodności. | `stages.scout` |
| 420 | `tematy_do_porownania(conn, limit)` | DB | Poprzednie artykuly w postaci NADAJACEJ SIE DO POROWNANIA. | `artykul_z_puli.wybierz_fakt`, `run.main` |
| 477 | `review(conn, run_id, card, draft)` | **$**(review) | Etap 8 — recenzja: rozliczenie kazdego zdania (DeepSeek V4 Pro). | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 513 | `ocen_forme(conn, run_id, draft)` | **$**(forma) | Obserwacja formy: beaty, eskalacja, moment przyłapania, znajomość otwarcia. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 534 | `ostatnie_uwagi(ile)` | — | Co zarzucono OSTATNIM artykulom — do promptu pisarza. | `audyt_systemu.main`, `stages.write` |
| 596 | `poprzednie_teksty(ile, pomin_tresc)` | — | Treści kilku ostatnich artykułów — materiał dla bramki ODCISK_FORMY. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 627 | `_nazwa_zrodla(conn, url)` | DB | Nazwa źródła zamiast gołego adresu. | `stages.save` |
| 649 | `save(conn, run_id, topic, card, draft, status, blocked_by, notes)` | DB | Etap 9 — zapis. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 700 | `pisarz_z_persona()` | — | Writing and prompt preview must choose the same persona route. | `stages.system_pisarza`, `stages.write` |
| 706 | `system_pisarza()` | — | System artykulu. | `stages.write` |
| 744 | `karta_dla_pisarza(card, teraz)` | — | Karta bez zastrzezenia, ktorego nie wolno opublikowac. | `stages.przygotuj_artykul_do_publikacji`, `stages.write` |
| 827 | `wstaw_date_zrodel(tekst, card)` | — | Stopka z data zrodel pisana PRZEZ KOD, nie przez model. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 884 | `write(conn, run_id, card, glebokosc)` | **$**(write) | Etap 7 — artykuł, modelem wybranym w presecie dla roli `write`. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 982 | `_ile_reakcji(k)` | — | „(reakcji: N)" TYLKO wtedy, gdy zrodlo to pole w ogole wypelnia. | `stages.wybierz_do_odpowiedzi` |
| 994 | `_po_rowno_ze_zrodel(komentarze, ile)` | — | Wycinek listy, ktory NIE MOZE zaglodzic zadnego miejsca rozmowy. | `stages.wybierz_do_odpowiedzi` |
| 1026 | `wybierz_do_odpowiedzi(conn, run_id, komentarze)` | **$**(wybor) | Komu odpisac, gdy komentarzy jest wiecej niz kilka. | `run.dzien`, `run.dzien.odpowiedzi` |
| 1103 | `reply_to(conn, run_id, comment, evidence)` | **$**(reply) | Odpowiedź na komentarz pod własną treścią — do szuflady. | `run.dzien`, `run.dzien.odpowiedzi` |
| 1192 | `plan_tygodnia(dzien_artykulu)` | DEAD? | Harmonogram tygodnia: co i kiedy wychodzi. | — |
| 1239 | `grafika(conn, run_id, draft, sciezka_artykulu)` | **$**((zmienna), grafika) | Nagłówek graficzny artykułu. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 1315 | `_wiek_konta_w_dniach(conn)` | DB | Ile dni działa to konto — liczone od pierwszego przebiegu w bazie. | `stages.budzet_dnia` |
| 1328 | `budzet_dnia(conn)` | — | Ile czego agent może dziś zrobić — losowane z widełek, nie stałe. | `run.dzien` |
| 1356 | `budzet_dnia.losuj(widelki)` | — | — | `stages.budzet_dnia`, `stages.budzet_dnia.z_miesiaca` |
| 1369 | `budzet_dnia.z_miesiaca(widelki)` | — | — | `stages.budzet_dnia` |
| 1393 | `_zapisz_budzet_dnia(dzien, budzet, rozbieg)` | — | Zapisuje, ile agent SOBIE ZALOZYL na ten dzien. | `stages.budzet_dnia` |
| 1442 | `sesje_dnia()` | DEAD? | Rozkłada dzień na kilka posiedzeń zamiast jednego ciągu. | — |
| 1469 | `losuj_odstep(co)` | — | Losuje przerwę, ale jej NIE odsypia. | `stages.odczekaj` |
| 1485 | `odczekaj(co, ile)` | DEAD? | Przerwa po działaniu, dobrana do tego, ile ono zajmuje CZLOWIEKOWI. | — |
| 1525 | `_klucz_faktu(tekst)` | — | Odcisk faktu odporny na przestawienie słów i inną liczbę w tym samym zdaniu. | `alarm.powtorki`, `stages.dopisz_kandydatow`, `stages.znajdz_ciekawostki` |
| 1531 | `tekst_faktu(x)` | — | Fakt bywa slownikiem (`{"fact": ..., "url": ...}`), a bywa samym zdaniem. | `stages.notki_dnia`, `stages.oznacz_uzyty`, `stages.wczytaj_zuzyte`, `stages.zapisz_zuzyte` |
| 1543 | `wczytaj_zuzyte()` | — | — | `alarm.powtorki`, `stages.zapisz_zuzyte`, `stages.znajdz_ciekawostki` |
| 1554 | `zapisz_zuzyte(nowe)` | — | Pamięć zużytych ciekawostek — poza bazą, bo budżet to cztery tabele. | `run.dzien`, `run.dzien.notki` |
| 1571 | `wybierz_cele(conn, run_id, posty)` | **$**(cele) | Które posty z kanału zasługują na komentarz. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` |
| 1643 | `zaczyn_z_kanalow(ile, ze_skrotem, max_dni, source_urls, exclude_urls, run_id)` | — | Tematy, o ktorych mowi sie w tym tygodniu — do promptu, nie do cytowania. | `personality._swiat`, `stages.notki_dnia`, `stages.scout`, `stages.znajdz_ciekawostki` |
| 1701 | `zaczyn_z_kanalow.priority(w)` | — | — | `stages.zaczyn_z_kanalow` |
| 1752 | `_rdzen_wydarzenia(w)` | — | Klucz zdarzenia: posortowane slowa rdzenia, zeby ta sama premiera opisana raz jako „acme, 5.3", a raz „5.3, acme" byla JEDNYM zdarzeniem. | `stages._nowe_wydarzenia`, `stages._zapamietaj_wydarzenia` |
| 1759 | `_nowe_wydarzenia(wydarzenia)` | — | Ktore z tych zdarzen sa NOWE — czyli nie dobieralismy juz o nich materialu. | `stages.znajdz_ciekawostki` |
| 1778 | `_nowe_wydarzenia._obsluzone_od(wpis)` | — | — | `stages._nowe_wydarzenia` |
| 1798 | `_wydarzenie_w_fakcie(w, fakt)` | — | Czy ten fakt jest O TYM wydarzeniu. | `stages._zapamietaj_wydarzenia` |
| 1819 | `_zapamietaj_wydarzenia(nowe, znane, ile, fakty)` | — | Zapisuje, ze o tych zdarzeniach material JUZ WROCIL. | `stages.znajdz_ciekawostki` |
| 1867 | `_przebiegi_z_bankiem_dzis(conn)` | DB | Ile PRZEBIEGOW dobieralo dzis material do banku. | `stages.znajdz_ciekawostki` |
| 1956 | `_polecenie_premiery(wydarzenia, ile)` | — | Polecenie o premierze do promptu ciekawostek — albo PUSTY NAPIS. | `stages.znajdz_ciekawostki` |
| 2001 | `znajdz_ciekawostki(conn, run_id, ile, na_artykul)` | **$**(curiosity) | Materiał na notki w dni bez artykułu. | `artykul_z_puli.wybierz_fakt`, `stages.notki_dnia` |
| 2379 | `kuplet_korygujacy(tekst)` | — | Czy tekst uzywa ruchu „nie X. | `stages.note` |
| 2397 | `zdania_z_tikiem(tekst)` | — | TE SAME trzy postacie tiku, ale oddane jako ZDANIA, nie jako „tak/nie". | `stages.kuplet_korygujacy`, `stages.note` |
| 2452 | `ostatnie_otwarcia(rodzaj, ile)` | — | Pierwsze slowa ostatnich notek — zeby kolejna nie zaczela sie tak samo. | `stages.comment_on`, `stages.note` |
| 2488 | `wiek_zrodla_w_dniach(data_zrodla, teraz)` | — | Ile dni ma zrodlo. | `stages.karta_dla_pisarza`, `stages.swiezosc_faktu`, `stages.swiezosc_karty` |
| 2538 | `nazywa_wersje(tekst)` | — | Czy zdanie nazywa konkretna wersje produktu. | `stages.swiezosc_faktu` |
| 2552 | `swiezosc_karty(card, teraz)` | — | Ile lat ma material, na ktorym stanie artykul. | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli._przebieg`, `run.main` |
| 2600 | `swiezosc_faktu(fakt, teraz)` | — | Czy ten fakt nadaje sie do wystawienia DZISIAJ. | `audyt_tematow.main`, `stages.wez_kandydatow`, `stages.znajdz_ciekawostki` |
| 2794 | `ostatnie_notki(ile)` | — | TRESCI ostatnich wystawionych notek — zeby nie napisac drugi raz tego samego. | `artykul_z_puli.wybierz_fakt`, `run.main` |
| 2825 | `_notki_z_dziennika(kawalek)` | — | Teksty UDANYCH notek z podanego kawalka dziennika, w kolejnosci zapisu. | `stages.ostatnie_notki`, `stages.pamiec_wystawionych` |
| 2886 | `_sygnatura_rdzeni()` | — | Odcisk SPOSOBU liczenia rdzeni, nie tresci. | `stages.pamiec_wystawionych` |
| 2905 | `_wczytaj_skrot_notek()` | — | Skrot z dysku albo pusty. | `stages.pamiec_wystawionych` |
| 2914 | `pamiec_wystawionych()` | — | Odciski WSZYSTKICH wystawionych notek. | `stages.notki_dnia` |
| 3033 | `_przytnij_pamiec(odciski)` | — | Zamienia odciski na zbiory i honoruje `config.PAMIEC_NOTEK`. | `stages.pamiec_wystawionych` |
| 3044 | `_zapisz_skrot_notek(odciski, bajtow, glowa, glowa_bajtow, sygnatura)` | — | Zapisuje skrot. | `stages.pamiec_wystawionych` |
| 3065 | `_opis_typu(note_type)` | — | Opis typu, a przy MYSLI takze PRZYDZIELONY ksztalt. | `stages.note` |
| 3081 | `note(conn, run_id, note_type, evidence, link, note_form, etap)` | **$**((zmienna)) | Jedna notka danego typu i danej FORMY — do szuflady. | `stages.notki_dnia` |
| 3245 | `note.powtarza_otwarcie(d)` | — | — | `stages.note` |
| 3400 | `_pola_ksztaltu(ksztalt, pomin)` | — | Nazwy pol z kontraktu na odpowiedz, bez klucza opakowujacego. | `stages (poziom modulu)` |
| 3427 | `zakwestionuj_promocje(url, powod)` | — | Artykul, ktorego notka promujaca odpadla na sprawdzeniu faktow. | `run.dzien`, `run.dzien.notki` |
| 3472 | `zapamietaj_niewystawiony(sciezka, powod)` | — | Zapisuje, ze gotowy artykul lezy na dysku i nie poszedl w swiat. | `artykul_z_puli._napisz_i_zapisz` |
| 3502 | `niewystawiony_artykul()` | — | Artykul czekajacy na ponowna probe, albo None. | `alarm.artykul_zalegly`, `run.dzien`, `run.dzien.zalegly_artykul`, `stages.odnotuj_probe_artykulu` |
| 3525 | `odnotuj_probe_artykulu(powod)` | — | Podbija licznik prob i oddaje nowa wartosc. | `run.dzien`, `run.dzien.zalegly_artykul` |
| 3540 | `zapomnij_niewystawiony()` | — | Tekst jest publiczny — znacznik znika. | `artykul_z_puli._napisz_i_zapisz`, `run.dzien`, `run.dzien.zalegly_artykul` |
| 3548 | `zapisz_do_promocji(url, tytul, tekst)` | — | Zapisuje opublikowany artykul do promowania przez kolejne dni. | `browser.wystaw_artykul` |
| 3568 | `wczytaj_promocje()` | — | — | `migracja_okno_promocji.main`, `stages.artykul_do_promocji`, `stages.odhacz_promocje`, `stages.recent_angles` *(+2)* |
| 3577 | `artykul_do_promocji()` | — | Artykul, ktory dzis czeka na notke promujaca — najwyzej JEDNA na dobe. | `migracja_okno_promocji.main`, `stages.notki_dnia` |
| 3637 | `odhacz_promocje(url, tekst)` | — | Odnotowuje, ze artykul dostal dzis swoja notke promujaca — I CO W NIEJ BYLO. | `run.dzien`, `run.dzien.notki` |
| 3690 | `_slowa(tekst)` | — | Znaczace slowa tekstu, obciete do rdzenia. | `stages._o_tym_samym`, `stages._sygnatura_rdzeni`, `stages.pamiec_wystawionych`, `stages.wez_kandydatow` *(+2)* |
| 3709 | `_zderzenie(x, y, min_wspolnych, prog)` | — | To samo pytanie co `_o_tym_samym`, ale na GOTOWYCH rdzeniach. | `stages._o_tym_samym`, `stages.wybierz_material` |
| 3725 | `nazwy_wlasne(tekst)` | — | Nazwy wlasne i identyfikatory z tekstu, sprowadzone do jednej postaci. | `stages.wspolna_nazwa` |
| 3773 | `wspolna_nazwa(a, b, korpus, maks_czestosc)` | — | Nazwa wlasna, ktora wystepuje w OBU tekstach i jest rzadka w korpusie. | `stages.wybierz_material` |
| 3806 | `_o_tym_samym(a, b, min_wspolnych, prog)` | — | Czy dwa teksty mowia o tej samej rzeczy. | `alarm.bank_bez_tematow`, `artykul_z_puli.wybierz_fakt`, `audyt_systemu.main`, `audyt_tematow.main` *(+6)* |
| 3856 | `teksty_ostatnich_notek(ile)` | — | Tresci ostatnich notek — do porownania po NAZWACH WLASNYCH. | `stages.note`, `stages.notki_dnia` |
| 3895 | `wybierz_material(zapas, unikaj, wczesniej, teksty)` | — | Bierze fakt, ktory NIE jest o tym samym, co juz dzis wystawiamy. | `stages.notki_dnia` |
| 3987 | `_chron_bank_notek()` | — | No publication happens during drafting: restore borrowed ideas on failure. | `stages.notki_dnia` |
| 4002 | `notki_dnia(conn, run_id, dzien_artykulu, karta, ciekawostki, link_artykulu, ile, od)` | — | Do pieciu notek z dziennego planu, kazda z innego materialu. | `run.dzien`, `run.dzien.notki` |
| 4338 | `ocen_restack(conn, run_id, notka)` | **$**(restack) | Czy podac te notke dalej i z jakim zdaniem. | `run.dzien`, `run.dzien.restacki` |
| 4417 | `_podloga_z_pamieci(tekst)` | — | Dwie podlogi, ktore dzialaja BEZ karty dowodowej. | `stages._zapora_komentarza`, `stages.comment_on`, `stages.ocen_restack` |
| 4435 | `_otwarcie_formulka(zdanie)` | — | Czy zdanie zaczyna sie od zapowiedzi ruchu zamiast od samego ruchu. | `stages.ocen_restack` |
| 4478 | `sprawdz_fakty(conn, run_id, post)` | **$**(factcheck) DEAD? | Szuka faktów do komentarza, zamiast pozwolić modelowi pisać z pamięci. | — |
| 4515 | `bez_wstrzykniecia(tekst, wlasny_adres_ok)` | — | Czy w naszym tekscie nie ma sladu cudzych POLECEN. | `stages._zapora_komentarza`, `stages._zapora_notki`, `stages.bramka_kandydata`, `stages.comment_on` *(+4)* |
| 4583 | `_status_twierdzenia(c)` | — | Status twierdzenia, znormalizowany. | `stages.napraw_obalone`, `stages.zweryfikuj` |
| 4607 | `przygotuj_artykul_do_publikacji(conn, run_id, draft, card, review_report)` | DB | Repair a factual problem within the existing quota; defer only this article. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 4650 | `przygotuj_artykul_do_publikacji.guard(text)` | — | — | `stages.przygotuj_artykul_do_publikacji` |
| 4676 | `zweryfikuj(conn, run_id, tekst, kontekst)` | **$**(factcheck) | Sprawdza to, co model NAPISAŁ — nie to, czego szukał przed pisaniem. | `stages.comment_on`, `stages.napraw_obalone`, `stages.note`, `stages.przygotuj_artykul_do_publikacji` |
| 4823 | `_zapora_notki(tekst)` | — | Pusty napis, gdy tekst notki przechodzi zapory. | `stages.note`, `stages.przygotuj_artykul_do_publikacji`, `stages.przygotuj_artykul_do_publikacji.guard` |
| 4834 | `_zapora_komentarza(tekst)` | — | To samo dla komentarza — ale komentarz ma zapore o jedna wiecej. | `stages.comment_on` |
| 4843 | `_liczby_zarzutu(c)` | — | Liczby z zarzutu, znormalizowane — po nich rozpoznajemy TEN SAM fakt. | `stages._ten_sam_zarzut` |
| 4858 | `_slowa_zarzutu(c)` | — | Slowa tresciowe z samego twierdzenia — drugi sygnal tozsamosci. | `stages._ten_sam_zarzut` |
| 4870 | `_adres_zarzutu(c)` | — | — | `stages._ten_sam_zarzut` |
| 4874 | `_ten_sam_zarzut(a, b)` | DEAD? | Czy dwa zarzuty mowia o tym samym fakcie. | — |
| 4918 | `napraw_obalone(conn, run_id, tekst, audyt, kontekst, min_slow, max_slow, etap, zapora)` | **$**((zmienna)) | Try one bounded repair, then validate the replacement independently. | `stages.comment_on`, `stages.note`, `stages.przygotuj_artykul_do_publikacji` |
| 5055 | `comment_on(conn, run_id, post, fakty)` | **$**(comment) | Komentarz do cudzego posta — do szuflady. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` |
| 5154 | `comment_on.powtarza_otwarcie(d)` | — | — | `stages.comment_on`, `stages.comment_on.napisz_kandydata` |
| 5172 | `comment_on.napisz_kandydata(i)` | **$**(comment) | Jeden kandydat albo None, gdy odpadl przed bramkami. | `stages.comment_on` |
| 5350 | `fallback_card(question, evidence)` | — | Karta złożona z dowodów bez modelu — gdy synteza padnie. | `artykul_z_puli._przebieg`, `run.main` |
| 5389 | `synthesis(conn, run_id, question, evidence)` | **$**(synthesis) | Etap 6 — karta dowodowa (DeepSeek V4 Pro). | `artykul_z_puli._przebieg`, `run.main` |
| 5447 | `_plaski(t)` | — | Tekst do porownania cytatu ze zrodlem — BIALE ZNAKI I TYPOGRAFIA, koniec. | `stages._jest_w_dokumencie` |
| 5461 | `_jest_w_dokumencie(cytat, dokument)` | — | Czy fragment naprawde stoi w tekscie, ktory model dostal. | `stages.classify` |
| 5467 | `classify(conn, run_id, question, corpus)` | **$**(classify) | Etap 5 — klasyfikacja i wyciąg fragmentów (DeepSeek). | `artykul_z_puli._przebieg`, `run.main` |
| 5571 | `_dobierz_przegladarka(conn, run_id, brakujace, juz_mamy)` | WWW DB | Drugie podejscie do stron, ktore zwyklemu pobieraniu daly pusty szkielet. | `stages.fetch` |
| 5632 | `fetch(conn, run_id, sources)` | DB | Etap 4 — pobranie stron. | `artykul_z_puli._przebieg`, `run.main` |
| 5801 | `_host(url)` | — | — | `stages._dobierz_przegladarka`, `stages.bank_fragmentow`, `stages.discovery`, `stages.fetch` |
| 5805 | `hosty_ktore_nigdy_nie_dzialaly(conn, min_prob)` | DB | Hosty, ktore probowalismy >=2 razy i ANI RAZU sie nie udalo. | `audyt_researchu.main`, `stages.discovery` |
| 5847 | `discovery(conn, run_id, question, recent_domains, tylko_pierwotne)` | **$**(discovery) | Etap 3 — dyskoveria zrodel (DeepSeek V4 Pro + web_search dostawcy). | `artykul_z_puli._przebieg`, `run.main` |
| 6031 | `feasibility(conn, run_id, topics)` | **$**(feasibility) | Etap 2 — tani odsiew przed drogą dyskoverią (DeepSeek). | `run.main` |
| 6055 | `podsumowanie_dzialan(dni)` | — | Ile czego WYSZLO w ostatnich `dni` dniach, wobec normy z configu. | `alarm.sprawdz_wszystko`, `alarm.wolumeny` |
| 6162 | `powody_porazek(dni)` | — | Dlaczego dzialania sie NIE UDALY — pogrupowane, najczestsze pierwsze. | `alarm.sprawdz_wszystko` |
| 6202 | `_powod_przegranej(klucz_zwyciezcy, klucz_tematu)` | — | Ktory skladnik klucza sortowania ROZSTRZYGNAL, i jakimi wartosciami. | `stages.pick_topic` |
| 6218 | `_pisze_do_produkcji(sciezka)` | — | Czy ta sciezka to PRAWDZIWY katalog danych, a nie katalog testu. | `stages.zapamietaj_niewystawiony`, `stages.zapisz_przegranych` |
| 6226 | `zapisz_przegranych(przegrani, run_id)` | DB | Dopisuje do dziennika tematy, ktore NIE wygraly, z powodem przegranej. | `stages.pick_topic` |
| 6278 | `pick_topic(topics, assessments, run_id, wczesniejsze)` | — | Wybiera temat leksykograficznie wedlug dziewieciu kryteriow. | `run.main` |
| 6295 | `pick_topic.temat(a)` | — | — | `stages.pick_topic`, `stages.pick_topic.artykulowy`, `stages.pick_topic.niepowtorzony`, `stages.pick_topic.nosny` *(+3)* |
| 6299 | `pick_topic.nosny(a)` | — | Czy temat niesie KTORAKOLWIEK z dwoch rzeczy: przekonanie albo stawke. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 6309 | `pick_topic.swiezy(a)` | — | Czy tego jeszcze nie opisano gdzie indziej. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 6322 | `pick_topic.wlasny_ranking(a)` | — | Gdzie model postawil ten temat wsrod SWOICH wlasnych propozycji. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 6332 | `pick_topic.watki(a)` | — | Ile osobnych pytan niesie temat. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 6336 | `pick_topic.artykulowy(a)` | — | Czy temat ma udokumentowana historie awarii I zasieg poza jedno miejsce. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 6347 | `pick_topic.niepowtorzony(a)` | — | Czy tego tematu nie opisalismy juz pod inna nazwa. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 6373 | `pick_topic.kolejnosc(a)` | — | — | `stages.pick_topic` |
| 6472 | `scout(conn, run_id, count)` | **$**(scout) | Etap 1 — skaut tematow. | `run.main` |
| 6620 | `scout.indeksy(klucz)` | — | Indeksy z rankingu: BEZ POWTORZEN, w kolejnosci podanej przez model. | `stages.scout`, `stages.scout.wazenie` |
| 6641 | `scout.wazenie(klucz, sila)` | — | Punkty MALEJACE z pozycja na liscie. | `stages.scout` |
| 6853 | `bank_fragmentow(conn, dni)` | DB | Nieuzyte fragmenty ze wszystkich artykulow — zaplacone i nieprzeczytane. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 6899 | `bibliotekarz(conn, run_id, bank)` | **$**(bibliotekarz) | Grupuje bank po MECHANIZMIE. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 6952 | `wczytaj_bank_notek()` | — | Gotowe notki czekajace na swoj moment. | `stages.dopisz_do_banku_notek`, `stages.stan_banku_notek`, `stages.wez_z_banku_notek` |
| 6963 | `dopisz_do_banku_notek(notki)` | DEAD? | Dokłada notki do banku, pomijajac te, ktore juz tam sa. | — |
| 6989 | `wez_z_banku_notek(ile)` | DB DEAD? | Wyjmuje najstarsze niewykorzystane notki i ZNACZY je jako wyjete. | — |
| 7009 | `stan_banku_notek()` | DEAD? | Ile mamy zapasu — do wypisania przy starcie przebiegu. | — |
| 7042 | `warto_pisac(conn, run_id, card)` | **$**(warto_pisac) | Etap przed pisarzem: czy jest tu luka, ktora obcy poczuje. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 7089 | `warto_pisac.jest(klucz)` | — | — | `stages.warto_pisac` |
| 7189 | `zbierz_pytania(wpisy)` | DB | Wyławia z odpowiedzi czytelnikow te, ktore sa PYTANIAMI, i zapisuje je. | `run.dzien`, `run.dzien.odpowiedzi` |
| 7232 | `wczytaj_pytania()` | — | Pula pytan czytelnikow. | `stages.pytania_dla_skauta`, `stages.zbierz_pytania` |
| 7242 | `pytania_dla_skauta(ile)` | — | Najswiezsze pytania czytelnikow, gotowe do wklejenia w prompt skauta. | `stages.scout` |
| 7247 | `_to_pdf(odpowiedz, url)` | — | Czy to PDF. | `stages.fetch` |
| 7266 | `_tekst_z_pdf(dane, max_stron)` | — | Warstwa tekstowa PDF-a. | `stages.fetch` |
| 7307 | `bramka_kandydata(k)` | — | Czy z tego da sie zrobic notke. | `audyt_tematow.main`, `stages.dopisz_kandydatow` |
| 7479 | `wczytaj_indeks()` | — | Indeks kandydatow. | `alarm.bank_bez_tematow`, `stages.bank_pelny`, `stages.dopisz_kandydatow`, `stages.oznacz_uzyty` *(+5)* |
| 7512 | `_zapisz_indeks(indeks)` | — | Zapis ATOMOWY: najpierw plik obok, potem podmiana jednym ruchem. | `stages.dopisz_kandydatow`, `stages.oznacz_uzyty`, `stages.posortuj_bank`, `stages.wez_kandydatow` *(+1)* |
| 7538 | `_stale_sygnaly(topics, pola)` | — | Ktore z pol mialy TE SAMA wartosc u WSZYSTKICH kandydatow. | `stages.pick_topic`, `stages.scout` |
| 7563 | `_precedens_ok(p)` | — | Czy ten wpis to naprawde precedens, a nie wypelniacz. | `stages.scout` |
| 7586 | `_wspolna_kotwica(a, b)` | — | Czy oba zdania mowia o tej samej NAZWIE albo tej samej LICZBIE. | `alarm.bank_bez_tematow`, `stages.dopisz_kandydatow` |
| 7600 | `_wspolna_kotwica.kotwice(t)` | — | — | `stages._wspolna_kotwica` |
| 7610 | `_bez_liczb(t)` | — | Zdanie z liczbami zastapionymi znacznikiem — do porownania szkieletu. | `stages._to_aktualizacja` |
| 7617 | `_to_aktualizacja(nowy, stary)` | — | TO SAMO ZDANIE, INNE LICZBY — czyli nowe ustalenie, nie powtorka. | `stages.dopisz_kandydatow` |
| 7659 | `dopisz_kandydatow(kandydaci)` | DB | Przepuszcza kandydatow przez bramke i dokłada do indeksu. | `stages.znajdz_ciekawostki` |
| 7795 | `wez_kandydatow(ile, na_artykul)` | DB | Wyjmuje kandydatow gotowych do pisania i ZNACZY ich jako uzytych. | `artykul_z_puli.wybierz_fakt`, `audyt_tematow.main`, `stages.notki_dnia` |
| 7924 | `wez_kandydatow._dzielą_rzadkie(a, b)` | — | Rzadkie slowo LUZUJE PROPORCJE, ale nie liczbe wspolnych rdzeni. | `stages.wez_kandydatow` |
| 7998 | `co_zadzialalo(ile)` | — | NASZE wlasne notki z ZMIERZONYM odbiorem — material dla sedziego banku. | `audyt_tematow.main`, `stages.posortuj_bank` |
| 8062 | `co_zadzialalo._wystawiona(r)` | — | — | `stages.co_zadzialalo` |
| 8080 | `_tabela_odbioru(naj, ile)` | — | Najlepiej i najgorzej przyjete notki, gotowe do wklejenia w prompt. | `stages.co_zadzialalo` |
| 8087 | `_tabela_odbioru.punkty(r)` | — | — | `stages._tabela_odbioru` |
| 8095 | `_tabela_odbioru.wiersz(r)` | — | — | `stages._tabela_odbioru` |
| 8137 | `posortuj_bank(conn, run_id, ile)` | **$**(bank) | Ustawia bank pomyslow od najmocniejszego i wyrzuca slabe. | `stages.notki_dnia` |
| 8343 | `_termin_waznosci(dni)` | — | Kiedy ta kandydatura przestaje byc tematem. | `stages.dopisz_kandydatow` |
| 8350 | `_z_obecnej_epoki(k)` | — | Czy ta kandydatura powstala PO ostatniej zmianie tematu konta. | `stages.bank_pelny`, `stages.posortuj_bank`, `stages.wez_kandydatow` |
| 8369 | `_po_terminie(k)` | — | Czy kandydatura jest juz po swoim terminie przydatnosci. | `audyt_tematow.main`, `stages.bank_pelny`, `stages.posortuj_bank`, `stages.wez_kandydatow` |
| 8391 | `bank_pelny()` | — | Czy zapas wystarczy, zeby NIE placic za nowe szukanie. | `audyt_tematow.main`, `stages.znajdz_ciekawostki` |
| 8409 | `zwroc_kandydatow(kandydaci)` | — | Oddaje do puli kandydatow, ktorych ostatecznie NIE uzyto. | `artykul_z_puli._przebieg`, `artykul_z_puli.wybierz_fakt`, `audyt_tematow.main`, `run.dzien` *(+3)* |
| 8451 | `oznacz_uzyty(fakt)` | DB | Odhacza w indeksie fakt, ktory NAPRAWDE poszedl w swiat. | `run.dzien`, `run.dzien.notki` |
| 8489 | `stan_indeksu()` | DEAD? | Ile mamy zapasu i ile odsialismy — do wypisania przy starcie. | — |
| 8513 | `korpus_fedreg(ile_dokumentow, ile_gestych)` | DEAD? | Preambuly przepisow, w ktorych regulator ODPOWIADA na zastrzezenia. | — |
| 8606 | `kandydaci_z_fedreg(conn, run_id, dokument)` | **$**(fedreg) DEAD? | Wyciaga kandydatow z jednej preambuly i oddaje w ksztalcie indeksu. | — |

---

<a id="agent-v2statystyki-py"></a>
## `agent-v2/statystyki.py`

Statystyki wystawionych pozycji: kto to zobaczyl i co z tego wyniklo.

11 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 84 | `_liczba(x)` | — | Cokolwiek z API -> int. | `stages._tabela_odbioru`, `stages._tabela_odbioru.punkty`, `statystyki._pozycje`, `statystyki._suma` *(+3)* |
| 126 | `_karty(dane)` | — | `cards` -> {cardId: karta}. | `statystyki.z_kart` |
| 144 | `_pozycje(karta)` | — | `items` listCarda -> {tytul: liczba}, w kolejnosci z API. | `statystyki._suma`, `statystyki.z_kart` |
| 168 | `_suma(karta)` | — | Liczba zbiorcza z karty: `value`, `count`, `total`, naglowek, suma pozycji. | `statystyki.z_kart` |
| 194 | `z_kart(dane)` | — | Odpowiedz `/api/v1/note_stats/c-{ID}` -> plaski rekord o stalych kluczach. | `browser.statystyki_pozycji` |
| 332 | `_plik()` | — | Sciezka liczona przy KAZDYM wywolaniu, nie raz przy imporcie. | `audyt_systemu.main`, `statystyki.wczytaj`, `statystyki.zapisz` |
| 343 | `zapisz(rodzaj, identyfikator, rekord, tekst)` | — | Dopisuje JEDEN pomiar. | `browser.statystyki_pozycji` |
| 387 | `wczytaj(rodzaj)` | — | Wszystkie pomiary z pliku, w kolejnosci zapisu. | `statystyki.najnowsze_per_pozycja`, `statystyki.podsumowanie` |
| 423 | `najnowsze_per_pozycja(rodzaj)` | — | {identyfikator: ostatni pomiar}. | `alarm._co_z_tego_wyszlo`, `raport_statystyk.main`, `stages.co_zadzialalo`, `statystyki.podsumowanie` |
| 448 | `podsumowanie(rodzaj)` | — | Sumy i srednie PO POZYCJACH, nie po pomiarach. | `raport_statystyk.main`, `wzajemnosc.kanaly` |
| 465 | `podsumowanie._suma_pola(pole)` | — | — | `statystyki.podsumowanie` |

---

<a id="agent-v2style-py"></a>
## `agent-v2/style.py`

Głos redakcyjny: korpus próbek i dwa profile stylu.

9 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 44 | `_plik_przypiec()` | — | — | `style.load_examples`, `style.przyklady_albo_pusto`, `style.wczytaj_przypiecia` |
| 52 | `_sha256(text)` | — | — | `style.load_examples` |
| 56 | `split_paragraphs(raw)` | — | Deterministyczny podział na akapity; styl końca linii nie zmienia numeracji. | `style.load_examples` |
| 63 | `bajty_kanoniczne(raw)` | — | Bajty korpusu niezależne od tego, jak git zmaterializował plik. | `style.load_examples`, `style.split_paragraphs` |
| 84 | `wczytaj_przypiecia()` | — | Przypięcia korpusu z pliku obok niego. | `style.load_examples` |
| 116 | `load_examples()` | — | Zwraca zatwierdzone fragmenty stylu albo rzuca, jeśli korpus się nie zgadza. | `style.przyklady_albo_pusto` |
| 163 | `przyklady_albo_pusto()` | — | Fragmenty stylu — albo pusta lista, gdy preset nie wymaga korpusu. | `stages.write` |
| 181 | `load_profiles()` | — | Profil pozytywny i negatywny stylu artykułu — z plikow wskazanych przez preset. | `stages.write` |
| 203 | `_z_marka(tekst)` | — | Podstawia `{marka}` w profilu stylu. | `style.load_profiles` |

---

<a id="agent-v2tekst-strony-py"></a>
## `agent-v2/tekst_strony.py`

Read explicitly marked article bodies before generic page extraction.

5 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 8 | `_ArticleBody.__init__(self)` | DEAD? | — | — |
| 14 | `_ArticleBody.handle_starttag(self, tag, attrs)` | DEAD? | — | — |
| 29 | `_ArticleBody.handle_endtag(self, tag)` | DEAD? | — | — |
| 37 | `_ArticleBody.handle_data(self, data)` | DEAD? | — | — |
| 47 | `tekst_z_html(body)` | DEAD? | Prefer publisher-marked prose, including an empty/unavailable body. | — |

---

<a id="agent-v2wzajemnosc-py"></a>
## `agent-v2/wzajemnosc.py`

Czy zaczepieni odwzajemniaja sie, i skad naprawde biora sie czytelnicy.

27 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 118 | `po_zmianie_tematu(kiedy)` | — | Czy ten wpis jest z obecnej epoki konta. | `wzajemnosc.odwzajemnienie`, `wzajemnosc.odwzajemnienie._od_kotwicy`, `wzajemnosc.zaczepienia` |
| 173 | `wczytaj(nazwa)` | — | Wiersze pliku JSONL z katalogu danych. | `wzajemnosc._nasze_pozycje`, `wzajemnosc._reakcje`, `wzajemnosc.kanaly`, `wzajemnosc.okno_pomiaru` *(+5)* |
| 201 | `_chwila(tekst)` | — | ISO-8601 na moment w UTC, bez strefy. | `wzajemnosc._licznik_z_chwili`, `wzajemnosc._nasze_pozycje`, `wzajemnosc._reakcje`, `wzajemnosc.kanaly` *(+7)* |
| 218 | `_nazwa(tekst)` | — | Nazwa wyswietlana do porownywania: male litery, jedna spacja. | `wzajemnosc._reakcje`, `wzajemnosc.kanaly`, `wzajemnosc.skad_przyszli` |
| 223 | `_uchwyt(tekst)` | — | Uchwyt do porownywania: male litery, same znaki alfanumeryczne. | `wzajemnosc.kanaly`, `wzajemnosc.odwzajemnienie` |
| 248 | `_licznik_z_chwili(kiedy, liczniki)` | — | Zapis `wzrost.jsonl` z tego samego momentu, co zrzut imienny — albo nic. | `wzajemnosc.pokrycie`, `wzajemnosc.zrzuty_czytelnikow` |
| 258 | `zrzuty_czytelnikow()` | — | Zrzuty po kolei, KAZDY Z OCENA, CZY NIE JEST OKROJONY. | `wzajemnosc.czytelnicy`, `wzajemnosc.naglowek`, `wzajemnosc.pomiar_oslepl`, `wzajemnosc.raport` |
| 317 | `czytelnicy()` | — | Uchwyt czytelnika -> co o nim wiemy ze zrzutow. | `wzajemnosc.kanaly`, `wzajemnosc.odwzajemnienie`, `wzajemnosc.opoznienia`, `wzajemnosc.skad_przyszli` |
| 380 | `kolejnosc(wpis, akcja)` | — | Czy czytelnik pojawil sie PO naszym dzialaniu, PRZED nim, czy nie wiadomo. | `wzajemnosc.odwzajemnienie` |
| 411 | `okno_pomiaru()` | — | Od kiedy do kiedy w ogole widzimy, kto nas czyta. | `wzajemnosc.naglowek`, `wzajemnosc.raport`, `wzajemnosc.slepe_okno` |
| 428 | `pokrycie()` | — | Ilu czytelnikow LICZY Substack, a ilu umiemy nazwac po imieniu. | `wzajemnosc.naglowek`, `wzajemnosc.raport` |
| 475 | `_pusty_kubel()` | — | Swiezy komplet licznikow. | `wzajemnosc.zaczepienia` |
| 484 | `zaczepienia()` | — | Kogo zaczepilismy — osobno udane, nieudane i POMINIETE. | `wzajemnosc.kanaly`, `wzajemnosc.odwzajemnienie`, `wzajemnosc.slepe_okno` |
| 530 | `odwzajemnienie()` | — | Ilu z zaczepionych pojawilo sie POTEM na naszej liscie czytelnikow. | `wzajemnosc.naglowek`, `wzajemnosc.opoznienia`, `wzajemnosc.raport` |
| 606 | `odwzajemnienie._od_kotwicy(lista)` | — | — | `wzajemnosc.odwzajemnienie` |
| 640 | `slepe_okno()` | — | O ile nasze najstarsze zaczepienie wyprzedza pierwszy zrzut czytelnikow. | `wzajemnosc.raport` |
| 668 | `_reakcje()` | — | Zdarzenia `skutek` rozdzielone na kubelki plus licznik typow nieznanych. | `wzajemnosc.kanaly`, `wzajemnosc.opoznienia`, `wzajemnosc.skad_przyszli` |
| 691 | `skad_przyszli()` | — | Ilu naszych czytelnikow zetknelo sie wczesniej z nasza trescia. | `wzajemnosc.naglowek`, `wzajemnosc.raport` |
| 751 | `_nasze_pozycje()` | — | Identyfikator wystawionej tresci -> rodzaj i chwila wystawienia. | `wzajemnosc.kanaly`, `wzajemnosc.opoznienia` |
| 779 | `kanal_reakcji(reakcja, pozycje)` | — | Ktorego NASZEGO kanalu dotknal czlowiek — z CELU reakcji, nie z jej typu. | `wzajemnosc.kanaly` |
| 806 | `opoznienia()` | — | Dwa rozne czasy, celowo NIE zsumowane w jeden. | `wzajemnosc.raport` |
| 900 | `kanaly()` | — | Co poprzedzilo pojawienie sie czytelnika — osobowo i pozycyjnie. | `wzajemnosc.raport` |
| 1024 | `pomiar_oslepl()` | — | Czy w ogole mamy z czego liczyc wzajemnosc. | `alarm.pomiar_wzajemnosci`, `wzajemnosc.main` |
| 1103 | `_procent(licznik, mianownik)` | — | — | `wzajemnosc.naglowek`, `wzajemnosc.raport` |
| 1107 | `naglowek()` | — | Jeden wiersz bez zrzutow albo cztery do szesciu. | `alarm.sprawdz_wszystko` |
| 1165 | `raport()` | — | Pelna odpowiedz na cztery pytania. | `alarm.przeglad`, `wzajemnosc.main` |
| 1449 | `main()` | — | — | `wzajemnosc (poziom modulu)` |

