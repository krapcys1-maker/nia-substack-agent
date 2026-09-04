# Function map — every function in the bot

**Generated** by `python narzedzia/mapa_funkcji.py`. Do not edit by hand.
Built from the modules' **syntax tree**, not from grepping for strings.

Scope: `agent-v2/*.py` only — what the systemd timers actually run.

The **what it does** column comes from each function's own docstring, so it is in Polish: that is the language of this codebase, and the README says so. Everything this generator writes itself is in English.

## Counts

| what | how many |
|---|---|
| modules | 25 |
| functions and methods | 551 |
| functions that call a paid model | 25 |
| functions that touch the browser | 62 |
| functions that touch the database | 41 |

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
| [`aktualne_modele.py`](#agent-v2aktualne-modele-py) | 4 | 1 | 0 | 0 | Jakie modele istnieja DZISIAJ — pytane na zywo, nie brane z pamieci. |
| [`alarm.py`](#agent-v2alarm-py) | 25 | 0 | 1 | 6 | Alarm do właściciela i kontrola zdrowia agenta. |
| [`artykul_z_puli.py`](#agent-v2artykul-z-puli-py) | 18 | 1 | 1 | 2 | Artykul bierze temat z tej samej puli, co notki. |
| [`audyt_researchu.py`](#agent-v2audyt-researchu-py) | 3 | 0 | 0 | 0 | Audyt segmentu researchu na ZYWYCH danych, jednym poleceniem. |
| [`audyt_systemu.py`](#agent-v2audyt-systemu-py) | 7 | 0 | 1 | 0 | Audyt CALEGO systemu na zywych danych, jednym poleceniem. |
| [`audyt_tematow.py`](#agent-v2audyt-tematow-py) | 4 | 0 | 0 | 0 | Audyt segmentu tematow — kazdy etap na ZYWYCH danych, jednym poleceniem. |
| [`bramki.py`](#agent-v2bramki-py) | 7 | 0 | 0 | 0 | Co moze zatrzymac tresc — wyliczone z kodu, nie spisane z pamieci. |
| [`browser.py`](#agent-v2browser-py) | 97 | 0 | 44 | 0 | Czytanie stron przeglądarką — tam, gdzie zwykły HTTP nie wystarcza. |
| [`config.py`](#agent-v2config-py) | 31 | 0 | 0 | 0 | Jedyne miejsce ze stałymi. |
| [`db.py`](#agent-v2db-py) | 11 | 0 | 0 | 7 | Baza: cztery tabele, waskie migracje kolumn, zero triggerow i limitow CHECK. |
| [`gates.py`](#agent-v2gates-py) | 21 | 0 | 0 | 0 | Bramki wykrywaja naruszenia, ale zadna nie blokuje artykulu. |
| [`jezyki.py`](#agent-v2jezyki-py) | 5 | 0 | 0 | 0 | Wzorce bramek ZALEZNE OD JEZYKA — i glosny sprzeciw, gdy jezyka nie ma. |
| [`kanal.py`](#agent-v2kanal-py) | 10 | 0 | 3 | 0 | Kanal czytelnika — jedyne zrodlo celow do komentowania. |
| [`konfiguracja.py`](#agent-v2konfiguracja-py) | 12 | 0 | 0 | 0 | Wczytanie `konfiguracja.toml` — jeden plik zamiast polowania po 88 plikach. |
| [`kopia_subskrybentow.py`](#agent-v2kopia-subskrybentow-py) | 4 | 0 | 1 | 0 | Kopia listy subskrybentow — jedyne aktywo, ktorego nie da sie odtworzyc. |
| [`korpus_kanalow.py`](#agent-v2korpus-kanalow-py) | 6 | 0 | 0 | 0 | Tematy z kanalow, ktore robia dokladnie to, co ma robic nasza publikacja. |
| [`llm.py`](#agent-v2llm-py) | 16 | 0 | 0 | 3 | Jedyna warstwa miedzy `run.py` a dostawca. |
| [`migracja_okno_promocji.py`](#agent-v2migracja-okno-promocji-py) | 2 | 0 | 0 | 0 | Jednorazowe uzupelnienie pola `dodane` w kolejce promocji. |
| [`norma.py`](#agent-v2norma-py) | 17 | 0 | 0 | 1 | Ile agent naprawde zrobil, dzien po dniu, wobec normy. |
| [`raport_statystyk.py`](#agent-v2raport-statystyk-py) | 5 | 0 | 0 | 0 | Co przyniosla kazda notka, restack i artykul — do czytania przez czlowieka. |
| [`run.py`](#agent-v2run-py) | 40 | 0 | 10 | 4 | Jedno polecenie uruchamiające — to samo lokalnie i na serwerze. |
| [`stages.py`](#agent-v2stages-py) | 159 | 23 | 1 | 18 | Etapy lancucha, po kolei, w pamieci. |
| [`statystyki.py`](#agent-v2statystyki-py) | 11 | 0 | 0 | 0 | Statystyki wystawionych pozycji: kto to zobaczyl i co z tego wyniklo. |
| [`style.py`](#agent-v2style-py) | 9 | 0 | 0 | 0 | Głos redakcyjny: korpus próbek i dwa profile stylu. |
| [`wzajemnosc.py`](#agent-v2wzajemnosc-py) | 27 | 0 | 0 | 0 | Czy zaczepieni odwzajemniaja sie, i skad naprawde biora sie czytelnicy. |

---

<a id="agent-v2aktualne-modele-py"></a>
## `agent-v2/aktualne_modele.py`

Jakie modele istnieja DZISIAJ — pytane na zywo, nie brane z pamieci.

4 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 69 | `_swieze(dane)` | — | Czy zapisana odpowiedz jest jeszcze wazna. | `aktualne_modele.pobierz` |
| 83 | `wczytaj()` | — | Ostatnia zapisana odpowiedz. | `aktualne_modele.jako_tekst`, `aktualne_modele.pobierz` |
| 94 | `pobierz(conn, run_id, wymus)` | **$**(aktualne_modele) | Aktualny stan modeli. | `aktualne_modele (poziom modulu)`, `stages.znajdz_ciekawostki` |
| 147 | `jako_tekst(dane)` | — | Stan modeli w postaci, ktora wchodzi do promptu. | `aktualne_modele (poziom modulu)`, `stages.znajdz_ciekawostki` |

---

<a id="agent-v2alarm-py"></a>
## `agent-v2/alarm.py`

Alarm do właściciela i kontrola zdrowia agenta.

**Wejscie produkcyjne:** `nia-alarm.timer`, raz na dobe 07:00 UTC: `alarm.py`

25 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 36 | `_ustawienia()` | — | — | `alarm.skonfigurowany`, `alarm.wyslij` |
| 49 | `skonfigurowany()` | — | — | `alarm (poziom modulu)`, `alarm.wyslij` |
| 54 | `_ostatnio(klucz)` | — | — | `alarm.wyslij` |
| 64 | `_zapisz(klucz)` | — | — | `alarm.wyslij` |
| 77 | `wyslij(klucz, temat, tresc)` | — | Wysyła alarm. | `alarm (poziom modulu)`, `alarm.sprawdz_przebiegi_i_ostrzez`, `alarm.sprawdz_sesje_i_ostrzez`, `alarm.sprawdz_wszystko` *(+2)* |
| 115 | `artykul_zalegly()` | — | Czy gotowy artykul lezy na dysku niewystawiony dluzej niz dobe. | `alarm.sprawdz_wszystko` |
| 140 | `sprawdz_sesje_i_ostrzez()` | WWW | Pilnuje jedynej rzeczy, która zatrzymuje agenta bez żadnego błędu. | `alarm (poziom modulu)`, `run.dzien` |
| 161 | `sprawdz_przebiegi_i_ostrzez(ile)` | DB | Alarmuje, gdy agent pada raz za razem. | `alarm (poziom modulu)` |
| 218 | `_polaczenie()` | DB | — | `alarm.cisza`, `alarm.koszt`, `alarm.przeglad`, `alarm.zawieszone` |
| 224 | `cisza()` | DB | Czy agent w ogole cos ostatnio zrobil. | `alarm.sprawdz_wszystko` |
| 251 | `zawieszone()` | DB | Przebiegi, ktore zostaly w stanie RUNNING na zawsze. | `alarm.sprawdz_wszystko` |
| 270 | `dysk()` | — | — | `alarm.sprawdz_wszystko` |
| 282 | `nadaktywnosc()` | — | Czy agent nie zapetlil sie i nie zasypuje Substacka. | `alarm.sprawdz_wszystko` |
| 330 | `koszt()` | DB | Czy zblizamy sie do sufitu — dziennego ALBO miesiecznego. | `alarm.przeglad`, `alarm.sprawdz_wszystko` |
| 387 | `wolumeny()` | — | Czy agent robi tyle, ile deklaruje — czy tylko wyglada, ze robi. | `alarm.sprawdz_wszystko` |
| 424 | `powtorki()` | — | Czy agent nie zaczal pisac wciaz tego samego. | `alarm.sprawdz_wszystko` |
| 443 | `kopia_subskrybentow()` | — | Czy istnieje AKTUALNA kopia listy subskrybentow. | `alarm.sprawdz_wszystko` |
| 492 | `pomiar_wzajemnosci()` | — | Czy nadal mamy z czego liczyc, kto sie odwzajemnia. | `alarm.sprawdz_wszystko` |
| 516 | `wydarzenie_bez_pokrycia()` | — | Wydarzenie odhaczone jako obsluzone, a w tresci ani slowa o nim. | `alarm.sprawdz_wszystko` |
| 543 | `wydarzenie_bez_pokrycia._kiedy(wpis)` | — | — | `alarm.wydarzenie_bez_pokrycia` |
| 599 | `bank_bez_tematow()` | — | Czy w banku zostalo dosc ROZNYCH tematow na dzisiejsze notki. | `alarm.sprawdz_wszystko` |
| 638 | `sprawdz_wszystko()` | — | Uruchamia komplet kontroli i alarmuje o tym, co znalazl. | `alarm (poziom modulu)` |
| 721 | `przeglad(dni)` | DB | Co agent NAPRAWDE zrobil przez ostatnie dni i gdzie sie pomylil. | `alarm (poziom modulu)` |
| 818 | `_co_z_tego_wyszlo(wpisy)` | — | Czy nasze dzialania w ogole wracaja — i ktore z nich. | `alarm.przeglad` |
| 856 | `_co_z_tego_wyszlo._ilu(warunek)` | — | — | `alarm._co_z_tego_wyszlo` |

---

<a id="agent-v2artykul-z-puli-py"></a>
## `agent-v2/artykul_z_puli.py`

Artykul bierze temat z tej samej puli, co notki.

**Wejscie produkcyjne:** `nia-artykul.timer`, wtorek 14:00 UTC: `artykul_z_puli.py --wyslij`

18 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 109 | `temat_z_faktu(conn, run_id, fakt)` | **$**(wybor) | Zamienia udokumentowany fakt w brief artykulu. | `artykul_z_puli._przebieg` |
| 146 | `glebokosc_z_oceny(ocena)` | — | RICH / SINGLE / THIN — liczone z tego, co `warto_pisac` ZOBACZYLO. | `artykul_z_puli._napisz_i_zapisz` |
| 184 | `glebokosc_z_oceny._surowy(pole)` | — | — | `artykul_z_puli.glebokosc_z_oceny`, `artykul_z_puli.glebokosc_z_oceny._filar` |
| 192 | `glebokosc_z_oceny._filar(pole)` | — | — | `artykul_z_puli.glebokosc_z_oceny` |
| 208 | `uniesie_artykul(brief)` | — | Czy z tego faktu da sie napisac TYSIAC SLOW, czy tylko dwa zdania. | `artykul_z_puli._przebieg` |
| 242 | `uniesie_artykul._pusty(s)` | — | — | `artykul_z_puli.uniesie_artykul` |
| 255 | `wybierz_fakt(conn, run_id, ile)` | — | Swiezy fakt z puli ciekawostek, ktory NIE powtarza zadnego artykulu. | `artykul_z_puli._przebieg` |
| 319 | `main()` | DB | Otwiera przebieg, oddaje robote i ZAMYKA go — takze przy wyjatku. | `artykul_z_puli (poziom modulu)` |
| 376 | `_zrob_miejsce_na_fakt(card)` | — | Robi miejsce na wstrzykniete twierdzenie, nie tracac zadnego ZRODLA. | `artykul_z_puli._przebieg` |
| 400 | `_zrob_miejsce_na_fakt._host(c)` | — | — | `artykul_z_puli._zrob_miejsce_na_fakt` |
| 419 | `_rozszerz_najstarsze(card, data_faktu)` | — | Data wstrzyknietego zrodla wazy — ale TYLKO w strone ostrzezenia. | `artykul_z_puli._przebieg` |
| 449 | `_przebieg(conn, run_id)` | DB | — | `artykul_z_puli.main` |
| 830 | `_katalog_ratunku()` | — | Katalog OBOK `ARTICLES_DIR`, nigdy w nim. | `artykul_z_puli._ratuj_tekst` |
| 854 | `_opublikuj(sciezka)` | WWW | Wystawia gotowy artykul, probujac wiecej niz raz. | `artykul_z_puli._napisz_i_zapisz` |
| 906 | `_ramka(powod, brak, katalog)` | — | Ostrzezenie, ktore idzie na POCZATEK `.md`, a nie tylko obok niego. | `artykul_z_puli._ratuj_tekst` |
| 976 | `_zrodla(card)` | — | Sekcja `## Sources` — bez pytania bazy o nazwy zrodel. | `artykul_z_puli._ratuj_tekst` |
| 994 | `_ratuj_tekst(run_id, brief, card, draft, etap, exc, raport)` | — | Gotowy tekst na dysk, gdy budzet albo wylacznik przerywa PO pisaniu. | `artykul_z_puli._napisz_i_zapisz` |
| 1118 | `_napisz_i_zapisz(conn, run_id, brief, card)` | — | Od bramki „warto pisac" do zapisu i grafiki. | `artykul_z_puli._przebieg` |

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

7 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 149 | `czy_pominiecie(rodzaj)` | — | Czy ten wpis jest pominieciem. | `audyt_systemu.main`, `audyt_systemu.policz_rodzaje` |
| 154 | `policz_rodzaje(wpisy)` | — | (udane, nieudane, pominiete) — trzy liczniki, bo stany naprawde sa trzy. | `audyt_systemu.main` |
| 177 | `etap(nr, nazwa)` | — | — | `audyt_systemu.main` |
| 184 | `werdykt(nazwa, stan, szczegol)` | — | — | `audyt_systemu.main` |
| 189 | `dziennik()` | — | — | `audyt_systemu.main` |
| 206 | `dzien(w)` | — | — | `audyt_systemu.main` |
| 210 | `main()` | WWW | — | `audyt_systemu (poziom modulu)` |

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

7 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 48 | `_zrodlo(nazwa)` | — | — | `bramki.przerwania_w_petlach`, `bramki.warunki_przed_wystawieniem`, `bramki.wstrzymania_publikacji` |
| 60 | `_komentarz_nad(linie, nr, ile)` | — | Ostatnia linia komentarza nad wskazanym wierszem — zwykle uzasadnienie. | `bramki.przerwania_w_petlach`, `bramki.wstrzymania_publikacji` |
| 74 | `_rodzic_funkcji(drzewo)` | — | Mapa: numer wiersza -> nazwa funkcji, w ktorej ten wiersz lezy. | `bramki.przerwania_w_petlach`, `bramki.warunki_przed_wystawieniem`, `bramki.wstrzymania_publikacji` |
| 84 | `wstrzymania_publikacji(pelne)` | — | Kazde miejsce, ktore ustawia `safe_to_post` na falsz. | `bramki.raport` |
| 113 | `warunki_przed_wystawieniem(pelne)` | — | Kazde wystawienie tresci i warunki, pod ktorymi stoi. | `bramki.raport` |
| 157 | `przerwania_w_petlach()` | — | `continue` i `return` w petlach po kandydatach — czyli „ten odpada". | `bramki.raport` |
| 207 | `raport(pelne)` | — | — | `bramki (poziom modulu)` |

---

<a id="agent-v2browser-py"></a>
## `agent-v2/browser.py`

Czytanie stron przeglądarką — tam, gdzie zwykły HTTP nie wystarcza.

97 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 44 | `wlasciwe_konto(page)` | DEAD? | Czy jestesmy na WLASCIWYM koncie tuz przed publikacja. | — |
| 84 | `pod_rzad_nieudanych(rodzaj)` | DEAD? | Ile porazek tego rodzaju poszlo BEZPOSREDNIO po sobie w tym przebiegu. | — |
| 93 | `slad_przebiegu()` | DEAD? | Podsumowanie tego, co ten proces zrobil — do wypisania na koncu. | — |
| 106 | `dopisz_wynik(rodzaj, wynik, **szczegoly)` | — | Jeden wpis na dzialanie — takze wtedy, gdy sie NIE UDALO, i z powodem. | `browser._klik_na_profilu`, `browser.obserwuj_profil`, `browser.polec_publikacje`, `browser.wystaw_artykul` *(+7)* |
| 217 | `zapisz_w_dzienniku(rodzaj, **szczegoly)` | — | Dziennik DZIALAN, nie wywolan modelu. | `browser.dopisz_skutki`, `browser.dopisz_wynik`, `browser.obserwuj_profil`, `browser.polub_w_kanale` *(+4)* |
| 241 | `z_dziennika_dzis()` | — | Ile komentarzy i polubien poszlo dzis — wedlug naszego zapisu. | `browser.ile_dzis_wystawione` |
| 307 | `naprawde_wyslac(wyslij, co)` | — | Ostatnie sito przed KAZDYM dzialaniem widocznym publicznie. | `browser._klik_na_profilu`, `browser.obserwuj_profil`, `browser.polec_publikacje`, `browser.polub_w_kanale` *(+7)* |
| 321 | `zalogowany(context)` | WWW | Twarde sprawdzenie: albo jest ciasteczko sesji, albo go nie ma. | `browser.sprawdz_serwer`, `browser.sprawdz_sesje`, `browser.zaloguj` |
| 326 | `dni_do_wygasniecia()` | — | Ile dni zostało sesji. | `alarm.sprawdz_sesje_i_ostrzez`, `browser.sprawdz_serwer`, `browser.sprawdz_sesje`, `browser.wymagaj_sesji` |
| 345 | `wymagaj_sesji()` | — | Sprawdza sesję przed pracą i mówi wprost, gdy trzeba się zalogować. | `browser._klik_na_profilu`, `browser.dopisz_skutki`, `browser.ile_dzis_wystawione`, `browser.kogo_polecamy` *(+22)* |
| 379 | `_chrome_odpowiada()` | — | — | `browser.podlacz_sie`, `browser.uruchom_chrome` |
| 389 | `uruchom_chrome()` | — | Otwiera Chrome na trwałym profilu agenta, jeśli jeszcze nie działa. | `browser.podlacz_sie` |
| 421 | `rozgrzej(context)` | WWW | Pozwala Cloudflare wydać zgodę dla adresu, z którego akurat działamy. | `browser.podlacz_sie` |
| 464 | `plaski(tekst)` | — | Tekst sprowadzony do znakow, ktore SAMI piszemy — do POROWNYWANIA. | `browser.numer_naszej_notki`, `browser.potwierdz_artykul`, `browser.potwierdz_komentarz`, `browser.potwierdz_odpowiedz` |
| 494 | `api_json(page, sciezka, baza)` | WWW | Czyta API WCHODZĄC na adres, zamiast wołać `fetch` ze strony. | `browser._artykuly_z_panelu`, `browser._watek_z_paginacja`, `browser.dopisz_skutki`, `browser.ile_dzis_wystawione` *(+19)* |
| 529 | `podlacz_sie()` | WWW | Podłącza się do Chrome'a, którego uruchomił i zalogował WŁAŚCICIEL. | `browser._klik_na_profilu`, `browser.dopisz_skutki`, `browser.ile_dzis_wystawione`, `browser.kogo_polecamy` *(+24)* |
| 626 | `sprawdz_sesje()` | WWW | Czy Chrome właściciela jest zalogowany i co agent w nim widzi. | `browser (poziom modulu)` |
| 660 | `sprawdz_serwer()` | WWW | Odpowiada na JEDNO pytanie: czy zapisana sesja żyje z adresu tego serwera. | `browser (poziom modulu)` |
| 708 | `zaloguj()` | WWW | Otwiera prawdziwe okno przeglądarki i czeka, aż właściciel się zaloguje. | `browser (poziom modulu)` |
| 764 | `rozpoznanie()` | WWW | Sprawdza, czy agent umie się poruszać po zalogowanym koncie. | `browser (poziom modulu)` |
| 835 | `_plaskie(galaz)` | — | Rozwija gałąź wątku do płaskiej listy komentarzy. | `browser._watek_z_paginacja`, `browser.juz_sie_odezwalismy`, `browser.nieodpowiedziane`, `browser.odpowiedzi_na_nasze_komentarze` *(+1)* |
| 850 | `_kiedy(c)` | — | — | `browser.komentarze_pod_artykulami`, `browser.nieodpowiedziane`, `browser.odpowiedzi_na_nasze_komentarze` |
| 859 | `ile_dzis_wystawione()` | WWW | Ile notek, komentarzy i polubien poszlo dzisiaj. | `run.dzien` |
| 927 | `statystyki_pozycji(pozycje)` | WWW | Pobiera statystyki NASZYCH tresci — jedna przegladarka na cala liste. | `run.dzien`, `run.dzien.odpowiedzi` |
| 1047 | `_ludzie_z_zakladki_ze_stanem(page)` | WWW | Kto jest na tej zakladce ORAZ czy zakladke w ogole udalo sie odczytac. | `browser._ludzie_z_zakladki`, `browser.kto_nas_czyta` |
| 1078 | `_ludzie_z_zakladki(page)` | — | Sama lista ludzi z zakladki. | `browser.odswiez_kogo_obserwujemy` |
| 1083 | `kto_nas_czyta(page)` | WWW | KTO nas obserwuje i subskrybuje — imiennie i z data. | `browser.zapisz_czytelnikow` |
| 1182 | `zapisz_czytelnikow(page)` | — | Zrzut listy czytelnikow do pliku, jeden wiersz na wywolanie. | `browser.nasze_pozycje_do_pomiaru` |
| 1279 | `kogo_obserwujemy()` | — | Kogo juz obserwujemy — Z DYSKU, BEZ SIECI. | `browser.czy_juz_obserwujemy`, `browser.odswiez_kogo_obserwujemy`, `browser.zapamietaj_obserwowanego`, `run.dzien` *(+2)* |
| 1306 | `_zapisz_kogo_obserwujemy(pamiec)` | — | Nigdy nie przerywa dzialania — to pamiec pomocnicza, nie warunek pracy. | `browser.odswiez_kogo_obserwujemy`, `browser.zapamietaj_obserwowanego` |
| 1319 | `zapamietaj_obserwowanego(uchwyt, host)` | — | Dopisuje JEDNEGO do pamieci — po udanej obserwacji albo po zastaniu „Unfollow" w menu. | `browser.obserwuj_profil`, `run.dzien`, `run.dzien.obserwuj` |
| 1342 | `czy_juz_obserwujemy(host, pamiec)` | — | Czy ten HOST wskazuje kogos, kogo juz obserwujemy. | `run.dzien`, `run.dzien.obserwuj` |
| 1362 | `odswiez_kogo_obserwujemy(page)` | WWW | Przepisuje pamiec ze strony `/@my/following`. | `browser.nasze_pozycje_do_pomiaru` |
| 1402 | `zapisz_wzrost_konta(profil)` | — | Ilu nas czyta DZISIAJ — jedna linia na pomiar, historia zostaje. | `browser.nasze_pozycje_do_pomiaru` |
| 1489 | `_wiersze_zrodel(dane)` | — | Lista pozycji z odpowiedzi o zrodlach — niezaleznie od klucza. | `browser._zapisy_ogolem`, `browser.zapisz_zrodla_ruchu` |
| 1502 | `_cos_w_odpowiedzi(dane)` | — | Czy odpowiedz W OGOLE cos niesie — odroznia „pusto" od „nie wiem". | `browser.zapisz_zrodla_ruchu` |
| 1527 | `_suma_pola(wiersze, *pola)` | — | Suma pierwszego istniejacego pola po wierszach. | `browser._z_totali`, `browser._zapisy_wezla`, `browser.zapisz_zrodla_ruchu` |
| 1548 | `_z_miar(wezel, nazwy)` | — | Liczba z `metrics: [{"name": "Subscribers", "total": 5}, ...]`. | `browser._z_totali`, `browser._zapisy_wezla` |
| 1566 | `_zapisy_wezla(wezel)` | — | Zapisy z jednej galezi — obojetne, w ktorym z dwoch ksztaltow przyszly. | `browser._zapisy_ogolem`, `browser._zapisy_per_notka` |
| 1573 | `_z_totali(dane, nazwy)` | — | Liczba z pola `totals` — panel podaje je LISTA, nie slownikiem. | `browser._zapisy_ogolem`, `browser.zapisz_zrodla_ruchu` |
| 1586 | `_zapisy_ogolem(dane)` | — | Laczna liczba zapisow z drzewa `growth/sources`, albo `None`. | `browser.zapisz_zrodla_ruchu` |
| 1602 | `_zapisy_per_notka(dane)` | — | {numer notki: zapisy} — z dowolnie zagniezdzonego drzewa. | `browser.zapisz_zrodla_ruchu` |
| 1627 | `zapisz_zrodla_ruchu(page, dni)` | WWW | SKAD naprawde biora sie zapisy — tabela zrodel, jedna linia na odczyt. | `browser.statystyki_pozycji` |
| 1831 | `_artykuly_z_panelu(page, baza)` | — | Nasze artykuly razem ze statystykami — JEDNYM zapytaniem. | `browser.nasze_pozycje_do_pomiaru` |
| 1876 | `_artykuly_z_panelu.licz(*klucze)` | — | — | `browser._artykuly_z_panelu` |
| 1913 | `nasze_pozycje_do_pomiaru(page, ile)` | — | Co wystawilismy i ma wlasny numer — czyli co da sie zmierzyc. | `browser.statystyki_pozycji` |
| 2078 | `dopisz_skutki()` | WWW | Dopisuje do dziennika, CO Z NASZYCH DZIALAN WYNIKLO. | `run.dzien`, `run.dzien.odpowiedzi` |
| 2229 | `odpowiedzi_na_nasze_komentarze(ile)` | WWW | Odpowiedzi na NASZE komentarze zostawione pod CUDZYMI tekstami. | `run.dzien`, `run.dzien.odpowiedzi` |
| 2341 | `komentarze_pod_artykulami(ile)` | WWW | Cudze komentarze pod NASZYMI artykulami, na ktore nie odpisalismy. | `run.dzien`, `run.dzien.odpowiedzi` |
| 2398 | `nieodpowiedziane(ile)` | WWW | Cudze odpowiedzi pod naszymi notkami, na które jeszcze nie odpisaliśmy. | `run.dzien`, `run.dzien.odpowiedzi` |
| 2457 | `sluchaj_publikacji(page)` | WWW | Zbiera kody odpowiedzi na zapytania PUBLIKUJACE. | `browser.wystaw_notke` |
| 2474 | `id_z_odpowiedzi(odpowiedzi)` | — | Identyfikator notki, ktory Substack oddal przy zapisie. | `browser.wystaw_notke` |
| 2507 | `numer_naszej_notki(page, tekst, prob)` | WWW | Numer notki odczytany z NASZEGO PROFILU po jej tresci. | `browser.potwierdz_notke`, `browser.restackuj_w_kanale`, `browser.wystaw_notke` |
| 2543 | `potwierdz_notke(page, tekst, prob)` | — | Pyta Substacka, czy notka naprawdę wisi na naszym profilu. | `browser.wystaw_notke` |
| 2574 | `_autor_przy_przycisku(przycisk)` | — | Kto napisal wpis, przy ktorym stoi ten przycisk. | `browser.polub_w_kanale` |
| 2622 | `_uchwyt_wezla(lokator)` | — | Uchwyt do KONKRETNEGO wezla DOM, albo None. | `browser.polub_w_kanale` |
| 2636 | `_stan_przycisku(uchwyt)` | — | Jak przycisk wyglada — wszystkie sygnaly naraz, sklejone w jeden napis. | `browser.polub_w_kanale`, `browser.potwierdz_polubienie` |
| 2661 | `potwierdz_polubienie(uchwyt, przed)` | — | Czy przycisk po klknieciu wyglada inaczej niz przed nim. | `browser.polub_w_kanale` |
| 2692 | `polub_w_kanale(ile, wyslij)` | WWW | Polubienia w kanale czytelnika. | `run.dzien`, `run.dzien.polubienia` |
| 2807 | `_klik_na_profilu(handle, napisy, rodzaj, wyslij)` | WWW | Klika JEDEN konkretny przycisk na cudzym profilu — i tylko jego. | `browser.zasubskrybuj` |
| 2876 | `pobierz_subskrybentow()` | WWW | Czyta liste subskrybentow z WLASNEGO panelu, wlasna sesja. | `kopia_subskrybentow.pobierz_z_panelu` |
| 2946 | `zloz_wiersze_subskrybentow(surowe)` | — | Sklada wiersze z komorek tabeli panelu: adres, typ i data rozpoczecia. | `browser._wiersze_subskrybentow` |
| 2984 | `_wiersze_subskrybentow(page)` | WWW | Czyta komorki tabeli z panelu i oddaje je zlozone. | `browser.pobierz_subskrybentow` |
| 3048 | `_pozycje_menu(page)` | WWW | Teksty pozycji OTWARTEGO menu, w kolejnosci ekranu. | `browser.obserwuj_profil`, `browser.potwierdz_obserwacje` |
| 3067 | `_otworz_menu_profilu(page)` | WWW | Klika kolko „..." w naglowku profilu. | `browser.obserwuj_profil`, `browser.potwierdz_obserwacje` |
| 3089 | `potwierdz_obserwacje(page)` | WWW | Czy menu profilu mowi teraz, ze go OBSERWUJEMY. | `browser.obserwuj_profil` |
| 3158 | `obserwuj_profil(handle, wyslij)` | WWW | Obserwuje cudzy profil — jego notki trafiaja do naszego kanalu. | `run.dzien`, `run.dzien.obserwuj` |
| 3320 | `kogo_polecamy(page)` | WWW | Kogo nasza publikacja poleca — z API, nie z pamieci. | `browser.polec_publikacje` |
| 3352 | `polec_publikacje(fraza, powod, wyslij)` | WWW DEAD? | Dodaje REKOMENDACJE publikacji. | — |
| 3459 | `zasubskrybuj(handle, wyslij)` | — | Subskrybuje cudzy profil. | `run.dzien`, `run.dzien.subskrybuj` |
| 3465 | `_esc(t)` | — | — | `browser.rozbierz_artykul` |
| 3469 | `rozbierz_artykul(sciezka)` | — | Rozkłada plik artykułu na tytuł, podtytuł i treść jako HTML. | `browser.wystaw_artykul` |
| 3552 | `wypelnij_artykul(page, artykul, obraz)` | WWW | Wkłada tytuł, podtytuł, grafikę i treść do otwartego edytora. | `browser.wystaw_artykul` |
| 3597 | `wstaw_przycisk_subskrypcji(page)` | WWW | Jeden przycisk subskrypcji, po ostatnim akapicie a przed źródłami. | `browser.wypelnij_artykul` |
| 3633 | `tresc_oswiadczenia()` | — | Oświadczenie „Jak to robię" — z pliku, nie z drugiej kopii w kodzie. | `browser.ustaw_oswiadczenie_ai` |
| 3648 | `ustaw_oswiadczenie_ai(wyslij)` | WWW DEAD? | Ustawia stałe oświadczenie pokazywane każdemu, kto skanuje nas pod kątem AI. | — |
| 3726 | `wystaw_odpowiedz_pod_artykulem(url_artykulu, autor, tekst, wyslij)` | WWW | Odpowiada pod KONKRETNYM komentarzem pod naszym artykułem. | `run.dzien`, `run.dzien.odpowiedzi` |
| 3840 | `potwierdz_artykul(page, tytul)` | — | Pyta Substacka, czy artykuł naprawdę jest opublikowany. | `browser.wystaw_artykul` |
| 3850 | `wystaw_artykul(sciezka_md, sciezka_png, wyslij)` | WWW | Wystawia artykuł na Substacku. | `artykul_z_puli._opublikuj`, `run.main` |
| 3947 | `_watek_z_paginacja(page, nid, stron)` | — | Caly watek notki — ze WSZYSTKICH stron, nie tylko z pierwszej. | `browser.potwierdz_komentarz`, `browser.potwierdz_odpowiedz` |
| 3980 | `potwierdz_odpowiedz(page, note_id, tekst)` | WWW | Pyta Substacka, czy nasza odpowiedź naprawdę jest w wątku — i KTORA. | `browser.wystaw_odpowiedz` |
| 4016 | `wystaw_odpowiedz(note_id, tekst, wyslij, kontekst, rodzaj)` | WWW | Odpowiada w watku — pod nasza notka albo w cudzej dyskusji. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.odpowiedzi` |
| 4187 | `wystaw_notke(tekst, wyslij, typ, forma, model)` | WWW | Wystawia notkę. | `run.dzien`, `run.dzien.notki` |
| 4308 | `zapamietaj_platny_host(host, prawo)` | — | Host, ktory wprost mowi, ze komentowac moga tylko placacy. | `browser.mozna_komentowac` |
| 4335 | `hosty_tylko_dla_placacych()` | — | Hosty, gdzie komentowac moga tylko placacy — do odsiania PRZED ocena. | `audyt_systemu.main`, `run.dzien`, `run.dzien.komentarze` |
| 4349 | `zapomnij_platny_host(host)` | — | Udany komentarz kasuje host z listy — wydawca mogl zmienic ustawienia. | `run.dzien`, `run.dzien.komentarze` |
| 4394 | `hosty_gdzie_komentarz_nie_wchodzi(min_prob, dni)` | — | Hosty, gdzie w ostatnich `dni` dniach probowalismy >=2 razy i ANI RAZ komentarz nie wszedl. | `browser.mozna_komentowac`, `run.dzien`, `run.dzien.komentarze` |
| 4514 | `mozna_komentowac(url)` | WWW | Czy pod tym tekstem wolno nam w ogóle napisać. | `run.dzien`, `run.dzien.komentarze` |
| 4582 | `uchwyt_publikacji(host)` | WWW | Nazwa konta do obserwowania — z hosta albo, gdy trzeba, z API. | `run.dzien`, `run.dzien.obserwuj`, `run.dzien.subskrybuj` |
| 4620 | `juz_sie_odezwalismy(page, url)` | — | Czy JUZ napisalismy cokolwiek pod tym postem albo pod ta notka. | `browser.wystaw_komentarz` |
| 4658 | `bez_znacznikow(html)` | — | Sam tekst, bez HTML-a. | `browser.wystaw_artykul` |
| 4668 | `potwierdz_adres_artykulu(page, tytul)` | — | Prawdziwy adres opublikowanego artykulu — od Substacka, nie z tytulu. | `browser.wystaw_artykul` |
| 4701 | `potwierdz_komentarz(page, url, tekst)` | WWW | Pyta Substacka, czy komentarz naprawdę wisi — zamiast wierzyć kliknięciu. | `browser.wystaw_komentarz`, `browser.wystaw_odpowiedz_pod_artykulem` |
| 4759 | `wystaw_komentarz(url, tekst, wyslij, kontekst)` | WWW | Wystawia komentarz pod cudzym postem. | `run.dzien`, `run.dzien.komentarze` |
| 4972 | `read_pages(urls)` | WWW | Otwiera strony w przeglądarce i zwraca ich widoczny tekst. | `run.dzien`, `run.dzien.komentarze`, `stages._dobierz_przegladarka` |
| 5009 | `restackuj_w_kanale(ile, decyzja, wyslij)` | WWW | Podaje dalej cudze notki z wlasnym zdaniem. | `run.dzien`, `run.dzien.restacki` |
| 5176 | `_notka_przy_przycisku(przycisk)` | — | Tresc i autor notki, przy ktorej stoi ten przycisk. | `browser.restackuj_w_kanale` |

---

<a id="agent-v2config-py"></a>
## `agent-v2/config.py`

Jedyne miejsce ze stałymi.

31 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 57 | `_korpus_stylu()` | — | — | `config (poziom modulu)` |
| 82 | `_env(name, default)` | — | — | `config (poziom modulu)` |
| 400 | `stawka_deepseek(model, kiedy)` | — | Stawka DeepSeeka z uwzglednieniem pory doby po wejsciu nowej taryfy. | `llm._cost` |
| 422 | `pora_na_publikacje(kiedy)` | — | Czy teraz wolno wystawiac NOTKI — wg zegara CZYTELNIKOW, nie serwera. | `run.dzien` |
| 468 | `w_szczycie(kiedy)` | DEAD? | Czy teraz obowiazuje droga taryfa. | — |
| 494 | `narzedzie_wyszukiwania(model)` | — | Nazwa narzedzia wyszukiwania i ewentualne ostrzezenie. | `llm._narzedzie_wyszukiwania` |
| 563 | `_dzis_utc()` | — | Dzisiejszy dzien UTC. | `config (poziom modulu)` |
| 585 | `sufit_dnia(dzien)` | — | Sufit obowiazujacy W TYM DNIU, nie dzisiaj. | `alarm.koszt`, `config (poziom modulu)` |
| 755 | `kotwica_dlugosci(glebokosc)` | — | Zdanie kalibrujace dlugosc, dobrane do ilosci materialu. | `stages.write` |
| 760 | `dlugosc_dla(glebokosc)` | — | Ile slow ma miec artykul o tej glebokosci. | `artykul_z_puli._napisz_i_zapisz`, `run.main`, `stages.write` |
| 912 | `_tokens_for(chars)` | — | — | `config (poziom modulu)` |
| 1286 | `losowa_postawa()` | — | Ktora postawa dla TEGO komentarza. | `stages.comment_on` |
| 1308 | `losowe_otwarcie()` | — | — | `stages.comment_on`, `stages.reply_to` |
| 1314 | `losowa_dlugosc()` | — | Ile slow ma miec ta konkretna wypowiedz. | `stages.comment_on`, `stages.reply_to` |
| 1720 | `losowy_ksztalt_mysli()` | — | Ktory ksztalt dostaje ta MYSL. | `stages._opis_typu` |
| 1871 | `normy_dzienne()` | — | Ile czego POWINNO wychodzic dziennie — srodek widelek. | `audyt_systemu.main`, `norma.main`, `stages.podsumowanie_dzialan` |
| 1959 | `_cisza_z_hasza(dzien)` | — | — | `config.cichy_dzien` |
| 1966 | `cichy_dzien(kiedy)` | — | Czy dzis nie nadajemy. | `audyt_systemu.main`, `norma.main`, `run.dzien`, `stages.podsumowanie_dzialan` |
| 2418 | `timeout_for(max_tokens)` | — | Termin w sekundach, który realnie pokrywa podany sufit tokenów. | `llm._call_claude`, `llm._call_deepseek`, `llm._call_deepseek_responses`, `llm._deepseek_pick_from_urls` |
| 2477 | `_znacznik_klienta(marka)` | — | — | `config._naglowek_klienta` |
| 2483 | `_naglowek_klienta()` | — | Naglowek User-Agent zlozony z BIEZACEJ nazwy marki. | `config (poziom modulu)` |
| 2512 | `_w_darmowym_tescie()` | — | Czy uruchomiony program to test, ktory NIE MA prawa placic. | `config (poziom modulu)` |
| 2567 | `pod_produkcyjnymi_danymi(sciezka)` | — | Czy ta sciezka lezy w PRAWDZIWYM katalogu danych (takze w podkatalogu). | `db._odmow_produkcji` |
| 2582 | `_moduly_projektu()` | — | Zaimportowane moduly z `agent-v2/`, bez samych testow. | `config.uzyj_katalogu_danych` |
| 2603 | `uzyj_katalogu_danych(katalog, utworz)` | DEAD? | Przestawia `DATA_DIR` I KOMPLET sciezek z niego policzonych. | — |
| 2631 | `uzyj_katalogu_danych.przeniesiona(wartosc)` | — | Ta sama sciezka wzgledem NOWEGO katalogu — albo None, gdy nie nasza. | `config.uzyj_katalogu_danych` |
| 2666 | `przywroc_katalog_danych(zdjecie)` | DEAD? | Cofa `uzyj_katalogu_danych`. | — |
| 2786 | `losowy_ruch_koncowy()` | — | Czym konczy sie TEN artykul. | `stages.write` |
| 2794 | `losowa_liczba_paraleli(glebokosc)` | — | Ile paraleli w drugim akcie. | `stages.write` |
| 2899 | `losowe_generatory(ile)` | — | Ktore wzorce w tym przebiegu. | `stages.znajdz_ciekawostki` |
| 2956 | `co_teraz_w_reku(kiedy)` | — | Rzeczy, ktorych czytelnik dotyka wlasnie teraz. | `stages.znajdz_ciekawostki` |

---

<a id="agent-v2db-py"></a>
## `agent-v2/db.py`

Baza: cztery tabele, waskie migracje kolumn, zero triggerow i limitow CHECK.

11 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 40 | `kanal(nazwa)` | — | Na czas bloku kazde zapisane wywolanie dostaje `akcja = nazwa`. | `run.main`, `stages._na_kanal`, `stages._na_kanal.zewnetrzny`, `stages._na_kanal.zewnetrzny.wewnetrzny` |
| 115 | `now()` | — | — | `db.finish_run`, `db.record_call`, `db.start_run`, `stages.dopisz_kandydatow` *(+6)* |
| 123 | `_odmow_produkcji(db_path)` | — | GLOSNA odmowa: wyjatek, nie ciche pominiecie. | `db.connect` |
| 167 | `connect(path)` | — | Otwiera bazę i zakłada schemat, jeśli go nie ma. | `alarm._polaczenie`, `alarm.sprawdz_przebiegi_i_ostrzez`, `artykul_z_puli.main`, `norma.przebiegow_dzis` *(+1)* |
| 198 | `_dopisz_brakujace_kolumny(conn)` | DB | — | `db.connect` |
| 216 | `start_run(conn, stage, tryb)` | DB | Nowy przebieg. | `artykul_z_puli.main`, `run.main` |
| 242 | `tryb_przebiegu(conn, run_id)` | DB | Tor, do ktorego nalezy przebieg. | `llm._preflight` |
| 253 | `finish_run(conn, run_id, status, stage, note)` | DB | — | `alarm.zawieszone`, `artykul_z_puli.main`, `run._done`, `run.main` |
| 265 | `record_call(conn, **fields)` | DB | Zapisuje wywołanie, wstawiając TYLKO te kolumny, które ktoś podał. | `llm.call`, `llm.obraz` |
| 300 | `spent_usd(conn, since_prefix, tryb)` | DB | Suma kosztów od znacznika czasu zaczynającego się danym prefiksem. | `alarm.koszt`, `llm._preflight`, `run.main` |
| 323 | `recent_domains(conn, limit)` | DB | Domeny z ostatnich N artykułów — wejście do reguły różnorodności. | `artykul_z_puli._przebieg`, `run.main` |

---

<a id="agent-v2gates-py"></a>
## `agent-v2/gates.py`

Bramki wykrywaja naruszenia, ale zadna nie blokuje artykulu.

21 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 66 | `_digit_tokens(text)` | — | — | `gates._korpus_pobranych`, `gates.deterministic_floors`, `gates.numbers_outside_corpus` |
| 70 | `_niepobrane(card)` | — | Twierdzenia oznaczone `not_fetched` — dolozone, nie wyciagniete. | `gates.deterministic_floors` |
| 82 | `_korpus_pobranych(card)` | — | Liczby z materialu, ktory NAPRAWDE pobralismy. | `gates.numbers_outside_corpus` |
| 103 | `numbers_outside_corpus(body, card)` | — | Liczby w tekście, których nie ma nigdzie w POBRANYM materiale. | `gates.deterministic_floors` |
| 109 | `deterministic_floors(body, card, poprzednie)` | — | Podłogi bez modelu: 0 USD, milisekundy, zero wywołań. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 206 | `_akapity(body)` | — | — | `gates.niewiadome_na_koncu`, `gates.odcisk_formy`, `gates.zakazane_otwarcie` |
| 211 | `zastrzezenia(body)` | — | Zastrzezenia w pierwszej osobie. | `gates.deterministic_floors` |
| 216 | `zakazane_otwarcie(body)` | — | Pierwsze zdanie, jesli kaze czytelnikowi isc cos obejrzec. | `gates.deterministic_floors` |
| 225 | `statystyki_bez_zrodla(body)` | — | Zdania, ktore niosa liczbe i udaja, ze maja na nia zrodlo. | `gates.deterministic_floors` |
| 234 | `niewiadome_na_koncu(body)` | — | Zbiorczy akapit o niewiadomych w ostatniej trzeciej tekstu. | `gates.deterministic_floors`, `gates.odcisk_formy` |
| 262 | `odcisk_formy(body)` | — | Zgrubny szkielet tekstu — do porownania z poprzednimi, nie do oceny. | `gates.powtorzona_forma` |
| 279 | `odcisk_formy.kubelek(u)` | — | — | `gates.odcisk_formy` |
| 298 | `powtorzona_forma(body, poprzednie, prog)` | — | Czy ten tekst ma ksztalt ktoregos z poprzednich. | `gates.deterministic_floors` |
| 329 | `uwagi_z_formy(obserwacja, body)` | — | Zamienia obserwacje modelu w uwagi. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 399 | `pozycja_w_tekscie(cytat, body)` | — | Gdzie w tekście stoi ten cytat, jako ułamek długości. | `run.main` |
| 411 | `szerokosc_podstawy(card)` | — | Na ilu ODREBNYCH serwisach stoja potwierdzone twierdzenia. | `gates.deterministic_floors` |
| 447 | `frazy_z_instrukcji(body, dlugosc)` | — | Czy pisarz wklein do tekstu wlasne polecenie. | `gates.deterministic_floors` |
| 459 | `frazy_z_instrukcji.slowa_z(tekst)` | — | — | `gates.frazy_z_instrukcji` |
| 462 | `frazy_z_instrukcji.ciagi(slowa)` | — | — | `gates.frazy_z_instrukcji` |
| 489 | `verdict(findings)` | — | Artykuł powstaje ZAWSZE. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 504 | `zapowiedziany_akapit_granic(body)` | — | Czy akapit o granicach zaczyna sie od zdania o samym sobie. | `gates.deterministic_floors` |

---

<a id="agent-v2jezyki-py"></a>
## `agent-v2/jezyki.py`

Wzorce bramek ZALEZNE OD JEZYKA — i glosny sprzeciw, gdy jezyka nie ma.

5 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 216 | `_ostrzez(jezyk, czego_brak)` | — | Raz na proces, ale GLOSNO. | `jezyki.frazy`, `jezyki.wzorzec` |
| 228 | `wzorzec(nazwa, jezyk)` | DEAD? | Skompilowany wzorzec bramki dla tego jezyka. | — |
| 237 | `frazy(nazwa, jezyk)` | DEAD? | Lista fraz dla tego jezyka. | — |
| 246 | `znane_jezyki()` | DEAD? | — | — |
| 250 | `brakujace(jezyk)` | DEAD? | Czego brakuje temu jezykowi wobec angielskiego. | — |

---

<a id="agent-v2kanal-py"></a>
## `agent-v2/kanal.py`

Kanal czytelnika — jedyne zrodlo celow do komentowania.

10 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 18 | `_historia()` | — | — | `kanal._za_niedawno_u_nich`, `kanal.posty_z_kanalu`, `kanal.zapamietaj_komentarz`, `run.dzien` *(+2)* |
| 29 | `zapamietaj_komentarz(post)` | — | Odnotowuje, u kogo dzis komentowalismy. | `run.dzien`, `run.dzien.komentarze` |
| 41 | `klucz_publikacji(post)` | — | Kim jest autor posta. | `kanal._za_niedawno_u_nich`, `kanal.posty_z_kanalu`, `kanal.zapamietaj_komentarz` |
| 48 | `_wiek_minut(data)` | — | — | `kanal._za_swiezy`, `run.opis_celu` |
| 58 | `_za_swiezy(post, widelki)` | — | Czy post jest na tyle swiezy, ze komentarz wygladalby jak czujka bota. | `kanal.notki_z_kanalu`, `kanal.posty_z_kanalu`, `kanal.szukaj_nowych` |
| 70 | `wartosc_celu(x)` | — | Klucz sortowania celow: WCZESNIE przed GLOSNO. | `kanal.notki_z_kanalu`, `kanal.szukaj_nowych` |
| 90 | `_za_niedawno_u_nich(post)` | — | Czy komentowalismy u tej publikacji w ostatnich dniach. | `kanal.posty_z_kanalu`, `kanal.szukaj_nowych` |
| 109 | `posty_z_kanalu(ile)` | WWW | Ostatnie posty z kanalu czytelnika, z liczba komentarzy i reakcji. | `run.dzien`, `run.dzien.komentarze` |
| 166 | `notki_z_kanalu(ile)` | WWW | Cudze notki, pod ktorymi mozna wejsc w dyskusje. | `run.dzien`, `run.dzien.dyskusje` |
| 214 | `szukaj_nowych(ile)` | WWW | Szuka NOWYCH kont wyszukiwarka Substacka, poza naszym kregiem. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` |

---

<a id="agent-v2konfiguracja-py"></a>
## `agent-v2/konfiguracja.py`

Wczytanie `konfiguracja.toml` — jeden plik zamiast polowania po 88 plikach.

12 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 62 | `_napis(v, gdzie)` | — | — | `konfiguracja (poziom modulu)` |
| 68 | `_data_albo_pusto(v, gdzie)` | — | Dzien w postaci RRRR-MM-DD albo pusty napis znaczacy „nigdy". | `konfiguracja (poziom modulu)` |
| 86 | `_liczba(v, gdzie)` | — | — | `konfiguracja (poziom modulu)` |
| 92 | `_prawda(v, gdzie)` | — | — | `konfiguracja (poziom modulu)` |
| 98 | `_lista_napisow(v, gdzie)` | — | — | `konfiguracja (poziom modulu)` |
| 105 | `_lista_napisow_moze_pusta(v, gdzie)` | — | Lista napisow, w ktorej PUSTA jest poprawna odpowiedzia. | `konfiguracja (poziom modulu)` |
| 121 | `_widelki(v, gdzie)` | — | Zakres [od, do]. | `konfiguracja (poziom modulu)` |
| 132 | `_slownik_list(v, gdzie)` | — | Tablica `klucz = [napisy]`. | `konfiguracja (poziom modulu)` |
| 152 | `_slownik_napisow(v, gdzie)` | — | — | `konfiguracja (poziom modulu)` |
| 224 | `sciezka(agent_dir)` | DEAD? | — | — |
| 228 | `wczytaj(plik)` | DEAD? | Surowa zawartosc pliku, sprawdzona co do ksztaltu. | — |
| 266 | `zastosuj(dane, cfg)` | DEAD? | Wklada wartosci do modulu `config`. | — |

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
| 130 | `main()` | — | — | `kopia_subskrybentow (poziom modulu)`, `run.dzien`, `run.dzien.kopia_listy` |

---

<a id="agent-v2korpus-kanalow-py"></a>
## `agent-v2/korpus_kanalow.py`

Tematy z kanalow, ktore robia dokladnie to, co ma robic nasza publikacja.

6 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 111 | `oczysc(tytul)` | — | Zdejmuje obietnice, zostawia zdarzenie. | `korpus_kanalow.przetworz` |
| 120 | `przetworz(wpisy)` | — | (nazwa_kanalu, element) -> kandydaci. | `korpus_kanalow.korpus_kanalow` |
| 173 | `_rdzen(temat)` | — | Slowa nosne tytulu — do porownywania, czy dwa kanaly mowia o tym samym. | `korpus_kanalow.wielkie_wydarzenia` |
| 184 | `_numer_wersji(slowo)` | — | Czy token wyglada na numer wydania: ma cyfre i nie jest rokiem. | `korpus_kanalow.wielkie_wydarzenia` |
| 192 | `wielkie_wydarzenia(korpus, min_kanalow, min_wspolnych, swiezosc_dni, min_kanalow_premiery)` | — | Rzeczy, o ktorych mowi NARAZ kilka roznych kanalow. | `audyt_tematow.main`, `stages.znajdz_ciekawostki` |
| 342 | `korpus_kanalow(ile)` | — | — | `audyt_tematow.main`, `korpus_kanalow (poziom modulu)`, `stages.zaczyn_z_kanalow`, `stages.znajdz_ciekawostki` |

---

<a id="agent-v2llm-py"></a>
## `agent-v2/llm.py`

Jedyna warstwa miedzy `run.py` a dostawca.

16 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 45 | `_dostawca(model)` | — | Czyj to model. | `llm._preflight`, `llm.call` |
| 63 | `_preflight(purpose, conn, run_id)` | DB | Warunki, które decydują, czy wywołanie może się w ogóle udać. | `llm.call`, `llm.obraz` |
| 177 | `_narzedzie_wyszukiwania(model)` | — | Nazwa narzedzia wyszukiwania; ostrzega RAZ NA PROCES o braku wpisu. | `llm._call_claude` |
| 186 | `_cost(model, tokens_in, tokens_out, web_searches, cache_hit)` | — | — | `llm.call` |
| 220 | `_log(purpose, model, tin, tout, searches, usd, verified)` | — | — | `llm.call` |
| 231 | `_call_claude(purpose, system, user, web_search)` | — | — | `llm.call` |
| 299 | `_call_deepseek_responses(purpose, system, user)` | — | DeepSeek przez /responses z server-side `web_search`. | `llm.call` |
| 350 | `_call_deepseek_responses.walk(node)` | — | — | `llm._call_deepseek_responses` |
| 407 | `_deepseek_pick_from_urls(purpose, system, user, urls)` | — | Drugie, tanie wywołanie: wybierz z adresów, które wyszukiwanie już zwróciło. | `llm._call_deepseek_responses` |
| 449 | `_call_deepseek(purpose, system, user)` | — | — | `llm.call` |
| 487 | `przejsciowy(exc)` | — | Czy ten błąd ma szansę minąć sam. | `llm.call` |
| 514 | `call(purpose, system, user, conn, run_id, web_search, collect_urls)` | DB | Woła model właściwy dla etapu i zapisuje koszt. | `aktualne_modele.pobierz`, `artykul_z_puli.temat_z_faktu`, `llm.ratuj_json`, `stages.bibliotekarz` *(+22)* |
| 623 | `obraz(opis, conn, run_id)` | DB | Generuje grafikę do artykułu i zapisuje jej koszt tam, gdzie resztę. | `stages.grafika` |
| 678 | `_obiekty_json(tekst)` | — | Kolejne ZBILANSOWANE obiekty JSON w tekscie, od lewej. | `llm.parse_json` |
| 743 | `ratuj_json(purpose, tekst, ksztalt, conn, run_id)` | — | Drugie podejście do odpowiedzi, która nie zawierała JSON-a. | `stages.discovery`, `stages.znajdz_ciekawostki` |
| 788 | `parse_json(text)` | — | Wyciąga obiekt JSON z odpowiedzi modelu. | `aktualne_modele.pobierz`, `artykul_z_puli.temat_z_faktu`, `stages.bibliotekarz`, `stages.classify` *(+21)* |

---

<a id="agent-v2migracja-okno-promocji-py"></a>
## `agent-v2/migracja_okno_promocji.py`

Jednorazowe uzupelnienie pola `dodane` w kolejce promocji.

2 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 34 | `daty_publikacji()` | — | Tytul artykulu -> data pierwszej udanej publikacji (YYYY-MM-DD). | `migracja_okno_promocji.main` |
| 62 | `main()` | — | — | `migracja_okno_promocji (poziom modulu)` |

---

<a id="agent-v2norma-py"></a>
## `agent-v2/norma.py`

Ile agent naprawde zrobil, dzien po dniu, wobec normy.

17 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 244 | `_zegar_agenta()` | — | Plik `.timer` agenta — znaleziony po TRESCI, nie po nazwie. | `norma (poziom modulu)` |
| 283 | `budzety_dzienne()` | — | Ile agent SOBIE ZALOZYL kazdego dnia — z pliku, nie z dzisiejszej konfiguracji. | `norma.main` |
| 332 | `_data(dzien)` | — | „2026-08-30" -> datetime w UTC. | `norma._poprawna_data`, `norma.dni_okna`, `norma.main` |
| 337 | `_poprawna_data(dzien)` | — | Czy da sie z tego zrobic date. | `norma.budzety_dzienne`, `norma.slad_dziennika`, `norma.wczytaj` |
| 354 | `wczytaj(dni)` | — | (zrobione, nieudane) — liczniki per dzien i rodzaj. | `norma.main` |
| 379 | `slad_dziennika(zalozone)` | — | (najstarszy znany dzien, zbior dni z JAKIMKOLWIEK wpisem w dzienniku). | `norma.main` |
| 425 | `_znak(ile, norma)` | — | Jak daleko od planu NA TEN DZIEN. | `norma._komorka`, `norma.main` |
| 464 | `dni_okna(dni, z_wpisami, zalozone, najstarszy)` | — | Wszystkie dni okna — TAKZE te, w ktorych nie wyszlo NIC. | `norma.main` |
| 509 | `_komorka(ile, cel, wyciszony, ma_wpisy, w_toku, szacowany)` | — | Jedna kratka tabeli. | `norma.main` |
| 534 | `przebiegow_dzis()` | DB | Ile przebiegow agenta domknelo sie dzis. | `norma.main` |
| 549 | `godziny_przebiegow()` | — | Minuty od polnocy UTC, o ktorych systemd odpala agenta. | `norma.przebiegow_naleznych` |
| 583 | `przebiegow_naleznych(teraz)` | — | (ile przebiegow POWINNO juz oddac swoja czesc, ile ich jest na dobe). | `norma.main` |
| 613 | `slad(dni)` | — | Gdzie dokladnie psuja sie publikacje — wg pozycji w serii i odstepu. | `norma.main` |
| 702 | `main()` | — | — | `norma (poziom modulu)` |
| 1006 | `main._srednia(r)` | — | None, gdy tej pozycji nie zmierzylismy ANI RAZU. | `norma.main`, `norma.main._procent_normy` |
| 1017 | `main._wykonanie(r)` | — | Ile z tego, co agent SOBIE ZALOZYL, naprawde zrobil. | `norma.main` |
| 1021 | `main._procent_normy(r)` | — | — | `norma.main` |

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
| 157 | `wzrost_konta()` | — | Ilu nas czyta i czy tego przybywa. | `raport_statystyk.main` |
| 215 | `main()` | — | — | `raport_statystyk (poziom modulu)` |

---

<a id="agent-v2run-py"></a>
## `agent-v2/run.py`

Jedno polecenie uruchamiające — to samo lokalnie i na serwerze.

**Wejscie produkcyjne:** `nia-agent.timer`, piec razy na dobe: `run.py --dzien --wyslij`

40 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 59 | `_utf8_stdout()` | — | Konsola Windows domyślnie cp1252 i wywala się na polskich znakach. | `run.main` |
| 72 | `cached(stage, produce, use_cache)` | — | Zapisuje wynik etapu i oddaje go z dysku zamiast płacić drugi raz. | `run.main` |
| 94 | `odmow_publikacji_z_kopii(wyslij)` | — | Kopia testowa nie ma prawa nic opublikowac. | `run.main` |
| 112 | `zajmij_zamek()` | — | Nie pozwala dwóm przebiegom działać naraz. | `run.main` |
| 144 | `opis_celu(cel)` | — | Co wiedzielismy o celu w chwili pisania — do dziennika. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` |
| 167 | `zostal_czas(na_co, potrzeba_s)` | — | Czy zdazymy jeszcze cokolwiek zrobic przed koncem czasu przebiegu. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze`, `run.dzien.notki` *(+4)* |
| 227 | `_pod_rzad_w_bloku(co, na_co)` | — | Ile porazek pod rzad naliczyl TEN blok, odkad sie zaczal. | `run.rytm` |
| 250 | `rytm(co, na_co, stan)` | — | Przerwa MIEDZY dwoma dzialaniami tego samego rodzaju. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze`, `run.dzien.notki` *(+3)* |
| 309 | `zmiesci_sie(rodzaj, ile, udzial)` | — | Ile z zaplanowanych dzialan NAPRAWDE zmiesci sie w czasie przebiegu. | `run.dzien` |
| 331 | `zmiesci_sie.potrzeba(n)` | — | — | `run.zmiesci_sie` |
| 344 | `ile_przebiegow_zostalo(conn)` | DB | Ile przebiegow dnia jeszcze bedzie, wliczajac biezacy. | `run.dzien` |
| 420 | `_po_zmianie_tematu(kiedy)` | — | Czy ten wpis jest z obecnej epoki konta. | `run.cele_wedlug_pierwszenstwa` |
| 499 | `_slug(tekst)` | — | Nazwa do porownywania: same litery i cyfry ASCII, malymi. | `run._reakcje_z_dziennika`, `run._slug_hosta` |
| 512 | `_slug_hosta(host)` | — | Pierwszy czlon adresu jako slug: `www.imienazwisko.com` -> `imienazwisko`. | `run.cele_wedlug_pierwszenstwa` |
| 520 | `_reakcje_z_dziennika()` | — | Jeden przebieg po dzienniku, dwie odpowiedzi o tych samych ludziach. | `run.kogo_juz_dotknelismy`, `run.reagujacy_jako_cele` |
| 614 | `kogo_juz_dotknelismy()` | — | Slugi nazw ludzi, ktorzy zareagowali na NASZA tresc — z dziennika. | `run.cele_wedlug_pierwszenstwa` |
| 638 | `nasi_czytelnicy()` | — | Uchwyty ludzi, ktorzy JUZ nas czytaja — z `czytelnicy.jsonl`. | `run.reagujacy_jako_cele` |
| 686 | `reagujacy_jako_cele()` | — | Ludzie, ktorzy zareagowali na nasza tresc, jako CELE WPROST. | `run.cele_wedlug_pierwszenstwa` |
| 769 | `_przeplot(pierwsza, druga)` | — | Na przemian z dwoch list; gdy jedna sie konczy, druga idzie dalej. | `run.cele_wedlug_pierwszenstwa` |
| 785 | `cele_wedlug_pierwszenstwa(historia)` | — | Hosty do zaczepienia, w kolejnosci pierwszenstwa. | `run.dzien`, `run.dzien.obserwuj`, `run.dzien.subskrybuj` |
| 894 | `powod_pustej_puli(rachunek)` | — | Zdanie do dziennika, gdy po odsianiu nie zostal nikt. | `run.dzien`, `run.dzien.obserwuj`, `run.dzien.subskrybuj` |
| 923 | `kogo_juz_subskrybujemy()` | — | Uchwyty, na ktore subskrypcja NIE MA JUZ CO wysylac. | `run.dzien`, `run.dzien.subskrybuj` |
| 985 | `czy_juz_subskrybujemy(host, zamkniete, pamiec)` | — | Czy ten HOST wskazuje konto, na ktore nie ma juz po co wchodzic. | `run.dzien`, `run.dzien.subskrybuj` |
| 1010 | `dzien(conn, run_id, wyslij)` | WWW | Jeden dzień pracy konta: notki, komentarze, odpowiedzi, polubienia. | `run.main` |
| 1128 | `dzien.blok(nazwa, robota)` | — | — | `run.dzien` |
| 1161 | `dzien.odpowiedzi()` | WWW | — | `run.dzien` |
| 1258 | `dzien.notki()` | WWW | — | `run.dzien`, `run.dzien.dyskusje` |
| 1340 | `dzien.komentarze()` | WWW | — | `run.dzien` |
| 1588 | `dzien.dyskusje()` | WWW | Wejscie w rozmowe pod cudza notka. | `run.dzien` |
| 1682 | `dzien.obserwuj()` | WWW | Obserwuje autorów, których teksty faktycznie czytaliśmy. | `run.dzien` |
| 1918 | `dzien.subskrybuj()` | WWW | Subskrybuje publikacje, ktore naprawde czytamy — i pilnuje dubli. | `run.dzien` |
| 2073 | `dzien.polubienia()` | WWW | — | `run.dzien` |
| 2078 | `dzien.restacki()` | WWW | Podanie dalej trafia do kanału NASZYCH obserwujących i powiadamia autora oryginału — za cenę jednego zdania zamiast całej notki. | `run.dzien` |
| 2113 | `dzien.zalegly_artykul()` | — | Dowozi tekst, ktory zostal na dysku po nieudanej publikacji. | `run.dzien` |
| 2173 | `dzien.kopia_listy()` | — | Jedyne aktywo, ktorego nie da sie odtworzyc — i jedyne miejsce, gdzie wlasciciel musial dotad cos kliknac. | `run.dzien` |
| 2222 | `_sygnal_ma_zostawic_slad()` | — | Zamienia SIGTERM na wyjatek, zeby przebieg zdazyl sie zapisac. | `run.main` |
| 2238 | `_sygnal_ma_zostawic_slad.podnies(numer, _ramka)` | — | — | `run._sygnal_ma_zostawic_slad` |
| 2248 | `main()` | WWW DB | — | `run (poziom modulu)` |
| 2856 | `_done(conn, run_id, stage)` | DB | — | `run.main` |
| 2862 | `_summary(conn, run_id)` | DB | — | `run._done`, `run.main` |

---

<a id="agent-v2stages-py"></a>
## `agent-v2/stages.py`

Etapy lancucha, po kolei, w pamieci.

159 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 50 | `_na_kanal(nazwa)` | DB | Wszystko, co ta funkcja zaplaci, ksieguje sie na kanal `nazwa`. | `artykul_z_puli.main`, `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` *(+16)* |
| 80 | `_na_kanal.zewnetrzny(f)` | DB | — | `stages._na_kanal` |
| 88 | `_na_kanal.zewnetrzny.wewnetrzny(*a, **k)` | DB | — | `stages._na_kanal.zewnetrzny` |
| 149 | `_blok_przykladow(klucz, gdy_pusto)` | — | Przyklady z niszy jako lista punktow — albo polecenie, gdy ich nie ma. | `stages._pola_wspolne` |
| 164 | `_pola_wspolne()` | — | Nisza, marka i jezyk — czytane z configu przy KAZDYM wywolaniu. | `stages._prompt` |
| 212 | `_prompt(name, **fields)` | — | — | `stages.bibliotekarz`, `stages.classify`, `stages.comment_on`, `stages.discovery` *(+18)* |
| 219 | `recent_angles(conn, limit)` | DB | Ostatnie kąty redakcyjne — wejście do reguły różnorodności. | `stages.scout` |
| 254 | `tematy_do_porownania(conn, limit)` | DB | Poprzednie artykuly w postaci NADAJACEJ SIE DO POROWNANIA. | `artykul_z_puli.wybierz_fakt`, `run.main` |
| 298 | `review(conn, run_id, card, draft)` | **$**(review) | Etap 8 — recenzja: rozliczenie kazdego zdania (DeepSeek V4 Pro). | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 318 | `ocen_forme(conn, run_id, draft)` | **$**(forma) | Obserwacja formy: beaty, eskalacja, moment przyłapania, znajomość otwarcia. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 339 | `ostatnie_uwagi(ile)` | — | Co zarzucono OSTATNIM artykulom — do promptu pisarza. | `audyt_systemu.main`, `stages.write` |
| 380 | `poprzednie_teksty(ile, pomin_tresc)` | — | Treści kilku ostatnich artykułów — materiał dla bramki ODCISK_FORMY. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 411 | `_nazwa_zrodla(conn, url)` | DB | Nazwa źródła zamiast gołego adresu. | `stages.save` |
| 433 | `save(conn, run_id, topic, card, draft, status, blocked_by, notes)` | DB | Etap 9 — zapis. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 484 | `karta_dla_pisarza(card, teraz)` | — | Karta bez zastrzezenia, ktorego nie wolno opublikowac. | `stages.write` |
| 539 | `wstaw_date_zrodel(tekst, card)` | — | Stopka z data zrodel pisana PRZEZ KOD, nie przez model. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 581 | `write(conn, run_id, card, glebokosc)` | **$**(write) | Etap 7 — artykuł (Claude). | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 654 | `_ile_reakcji(k)` | — | „(reakcji: N)" TYLKO wtedy, gdy zrodlo to pole w ogole wypelnia. | `stages.wybierz_do_odpowiedzi` |
| 666 | `_po_rowno_ze_zrodel(komentarze, ile)` | — | Wycinek listy, ktory NIE MOZE zaglodzic zadnego miejsca rozmowy. | `stages.wybierz_do_odpowiedzi` |
| 698 | `wybierz_do_odpowiedzi(conn, run_id, komentarze)` | **$**(wybor) | Komu odpisac, gdy komentarzy jest wiecej niz kilka. | `run.dzien`, `run.dzien.odpowiedzi` |
| 775 | `reply_to(conn, run_id, comment, evidence)` | **$**(reply) | Odpowiedź na komentarz pod własną treścią — do szuflady. | `run.dzien`, `run.dzien.odpowiedzi` |
| 850 | `plan_tygodnia(dzien_artykulu)` | DEAD? | Harmonogram tygodnia: co i kiedy wychodzi. | — |
| 897 | `grafika(conn, run_id, draft, sciezka_artykulu)` | **$**((zmienna), grafika) | Nagłówek graficzny artykułu. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 966 | `_wiek_konta_w_dniach(conn)` | DB | Ile dni działa to konto — liczone od pierwszego przebiegu w bazie. | `stages.budzet_dnia` |
| 979 | `budzet_dnia(conn)` | — | Ile czego agent może dziś zrobić — losowane z widełek, nie stałe. | `run.dzien` |
| 1007 | `budzet_dnia.losuj(widelki)` | — | — | `stages.budzet_dnia`, `stages.budzet_dnia.z_miesiaca` |
| 1020 | `budzet_dnia.z_miesiaca(widelki)` | — | — | `stages.budzet_dnia` |
| 1044 | `_zapisz_budzet_dnia(dzien, budzet, rozbieg)` | — | Zapisuje, ile agent SOBIE ZALOZYL na ten dzien. | `stages.budzet_dnia` |
| 1093 | `sesje_dnia()` | DEAD? | Rozkłada dzień na kilka posiedzeń zamiast jednego ciągu. | — |
| 1120 | `losuj_odstep(co)` | — | Losuje przerwę, ale jej NIE odsypia. | `stages.odczekaj` |
| 1136 | `odczekaj(co, ile)` | DEAD? | Przerwa po działaniu, dobrana do tego, ile ono zajmuje CZLOWIEKOWI. | — |
| 1176 | `_klucz_faktu(tekst)` | — | Odcisk faktu odporny na przestawienie słów i inną liczbę w tym samym zdaniu. | `alarm.powtorki`, `stages.dopisz_kandydatow`, `stages.znajdz_ciekawostki` |
| 1182 | `tekst_faktu(x)` | — | Fakt bywa slownikiem (`{"fact": ..., "url": ...}`), a bywa samym zdaniem. | `stages.notki_dnia`, `stages.wczytaj_zuzyte`, `stages.zapisz_zuzyte` |
| 1194 | `wczytaj_zuzyte()` | — | — | `alarm.powtorki`, `stages.zapisz_zuzyte`, `stages.znajdz_ciekawostki` |
| 1205 | `zapisz_zuzyte(nowe)` | — | Pamięć zużytych ciekawostek — poza bazą, bo budżet to cztery tabele. | `run.dzien`, `run.dzien.notki` |
| 1222 | `wybierz_cele(conn, run_id, posty)` | **$**(cele) | Które posty z kanału zasługują na komentarz. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` |
| 1287 | `zaczyn_z_kanalow(ile)` | — | Tematy, o ktorych mowi sie w tym tygodniu — do promptu, nie do cytowania. | `stages.notki_dnia`, `stages.scout`, `stages.znajdz_ciekawostki` |
| 1312 | `_rdzen_wydarzenia(w)` | — | Klucz zdarzenia: posortowane slowa rdzenia, zeby ta sama premiera opisana raz jako „acme, 5.3", a raz „5.3, acme" byla JEDNYM zdarzeniem. | `stages._nowe_wydarzenia`, `stages._zapamietaj_wydarzenia` |
| 1319 | `_nowe_wydarzenia(wydarzenia)` | — | Ktore z tych zdarzen sa NOWE — czyli nie dobieralismy juz o nich materialu. | `stages.znajdz_ciekawostki` |
| 1338 | `_nowe_wydarzenia._obsluzone_od(wpis)` | — | — | `stages._nowe_wydarzenia` |
| 1358 | `_zapamietaj_wydarzenia(nowe, znane, ile)` | — | Zapisuje, ze o tych zdarzeniach material JUZ WROCIL. | `stages.znajdz_ciekawostki` |
| 1389 | `_przebiegi_z_bankiem_dzis(conn)` | DB | Ile PRZEBIEGOW dobieralo dzis material do banku. | `stages.znajdz_ciekawostki` |
| 1472 | `_polecenie_premiery(wydarzenia, ile)` | — | Polecenie o premierze do promptu ciekawostek — albo PUSTY NAPIS. | `stages.znajdz_ciekawostki` |
| 1517 | `znajdz_ciekawostki(conn, run_id, ile)` | **$**(curiosity) | Materiał na notki w dni bez artykułu. | `artykul_z_puli.wybierz_fakt`, `stages.notki_dnia` |
| 1809 | `kuplet_korygujacy(tekst)` | — | Czy tekst uzywa ruchu „nie X. | `stages.note` |
| 1827 | `zdania_z_tikiem(tekst)` | — | TE SAME trzy postacie tiku, ale oddane jako ZDANIA, nie jako „tak/nie". | `stages.kuplet_korygujacy`, `stages.note` |
| 1882 | `ostatnie_otwarcia(rodzaj, ile)` | — | Pierwsze slowa ostatnich notek — zeby kolejna nie zaczela sie tak samo. | `stages.comment_on`, `stages.note` |
| 1918 | `wiek_zrodla_w_dniach(data_zrodla, teraz)` | — | Ile dni ma zrodlo. | `stages.karta_dla_pisarza`, `stages.swiezosc_faktu`, `stages.swiezosc_karty` |
| 1968 | `nazywa_wersje(tekst)` | — | Czy zdanie nazywa konkretna wersje produktu. | `stages.swiezosc_faktu` |
| 1982 | `swiezosc_karty(card, teraz)` | — | Ile lat ma material, na ktorym stanie artykul. | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli._przebieg`, `run.main` |
| 2030 | `swiezosc_faktu(fakt, teraz)` | — | Czy ten fakt nadaje sie do wystawienia DZISIAJ. | `audyt_tematow.main`, `stages.wez_kandydatow`, `stages.znajdz_ciekawostki` |
| 2224 | `ostatnie_notki(ile)` | — | TRESCI ostatnich wystawionych notek — zeby nie napisac drugi raz tego samego. | `artykul_z_puli.wybierz_fakt`, `run.main` |
| 2255 | `_notki_z_dziennika(kawalek)` | — | Teksty UDANYCH notek z podanego kawalka dziennika, w kolejnosci zapisu. | `stages.ostatnie_notki`, `stages.pamiec_wystawionych` |
| 2316 | `_sygnatura_rdzeni()` | — | Odcisk SPOSOBU liczenia rdzeni, nie tresci. | `stages.pamiec_wystawionych` |
| 2335 | `_wczytaj_skrot_notek()` | — | Skrot z dysku albo pusty. | `stages.pamiec_wystawionych` |
| 2344 | `pamiec_wystawionych()` | — | Odciski WSZYSTKICH wystawionych notek. | `stages.notki_dnia` |
| 2463 | `_przytnij_pamiec(odciski)` | — | Zamienia odciski na zbiory i honoruje `config.PAMIEC_NOTEK`. | `stages.pamiec_wystawionych` |
| 2474 | `_zapisz_skrot_notek(odciski, bajtow, glowa, glowa_bajtow, sygnatura)` | — | Zapisuje skrot. | `stages.pamiec_wystawionych` |
| 2495 | `_opis_typu(note_type)` | — | Opis typu, a przy MYSLI takze PRZYDZIELONY ksztalt. | `stages.note` |
| 2511 | `note(conn, run_id, note_type, evidence, link, note_form, etap)` | **$**((zmienna)) | Jedna notka danego typu i danej FORMY — do szuflady. | `stages.notki_dnia` |
| 2627 | `note.powtarza_otwarcie(d)` | — | — | `stages.note` |
| 2734 | `_pola_ksztaltu(ksztalt, pomin)` | — | Nazwy pol z kontraktu na odpowiedz, bez klucza opakowujacego. | `stages (poziom modulu)` |
| 2754 | `zakwestionuj_promocje(url, powod)` | — | Artykul, ktorego notka promujaca odpadla na sprawdzeniu faktow. | `run.dzien`, `run.dzien.notki` |
| 2799 | `zapamietaj_niewystawiony(sciezka, powod)` | — | Zapisuje, ze gotowy artykul lezy na dysku i nie poszedl w swiat. | `artykul_z_puli._napisz_i_zapisz` |
| 2825 | `niewystawiony_artykul()` | — | Artykul czekajacy na ponowna probe, albo None. | `alarm.artykul_zalegly`, `run.dzien`, `run.dzien.zalegly_artykul`, `stages.odnotuj_probe_artykulu` |
| 2836 | `odnotuj_probe_artykulu(powod)` | — | Podbija licznik prob i oddaje nowa wartosc. | `run.dzien`, `run.dzien.zalegly_artykul` |
| 2851 | `zapomnij_niewystawiony()` | — | Tekst jest publiczny — znacznik znika. | `artykul_z_puli._napisz_i_zapisz`, `run.dzien`, `run.dzien.zalegly_artykul` |
| 2859 | `zapisz_do_promocji(url, tytul, tekst)` | — | Zapisuje opublikowany artykul do promowania przez kolejne dni. | `browser.wystaw_artykul` |
| 2877 | `wczytaj_promocje()` | — | — | `migracja_okno_promocji.main`, `stages.artykul_do_promocji`, `stages.odhacz_promocje`, `stages.recent_angles` *(+2)* |
| 2886 | `artykul_do_promocji()` | — | Artykul, ktory dzis czeka na notke promujaca — najwyzej JEDNA na dobe. | `migracja_okno_promocji.main`, `stages.notki_dnia` |
| 2940 | `odhacz_promocje(url, tekst)` | — | Odnotowuje, ze artykul dostal dzis swoja notke promujaca — I CO W NIEJ BYLO. | `run.dzien`, `run.dzien.notki` |
| 2993 | `_slowa(tekst)` | — | Znaczace slowa tekstu, obciete do rdzenia. | `stages._o_tym_samym`, `stages._sygnatura_rdzeni`, `stages.pamiec_wystawionych`, `stages.wez_kandydatow` *(+2)* |
| 3012 | `_zderzenie(x, y, min_wspolnych, prog)` | — | To samo pytanie co `_o_tym_samym`, ale na GOTOWYCH rdzeniach. | `stages._o_tym_samym`, `stages.wybierz_material` |
| 3028 | `nazwy_wlasne(tekst)` | — | Nazwy wlasne i identyfikatory z tekstu, sprowadzone do jednej postaci. | `stages.wspolna_nazwa` |
| 3076 | `wspolna_nazwa(a, b, korpus, maks_czestosc)` | — | Nazwa wlasna, ktora wystepuje w OBU tekstach i jest rzadka w korpusie. | `stages.wybierz_material` |
| 3109 | `_o_tym_samym(a, b, min_wspolnych, prog)` | — | Czy dwa teksty mowia o tej samej rzeczy. | `alarm.bank_bez_tematow`, `artykul_z_puli.wybierz_fakt`, `audyt_systemu.main`, `audyt_tematow.main` *(+6)* |
| 3159 | `teksty_ostatnich_notek(ile)` | — | Tresci ostatnich notek — do porownania po NAZWACH WLASNYCH. | `stages.note`, `stages.notki_dnia` |
| 3198 | `wybierz_material(zapas, unikaj, wczesniej, teksty)` | — | Bierze fakt, ktory NIE jest o tym samym, co juz dzis wystawiamy. | `stages.notki_dnia` |
| 3287 | `notki_dnia(conn, run_id, dzien_artykulu, karta, ciekawostki, link_artykulu, ile, od)` | — | Do pieciu notek z dziennego planu, kazda z innego materialu. | `run.dzien`, `run.dzien.notki` |
| 3562 | `ocen_restack(conn, run_id, notka)` | **$**(restack) | Czy podac te notke dalej i z jakim zdaniem. | `run.dzien`, `run.dzien.restacki` |
| 3638 | `_podloga_z_pamieci(tekst)` | — | Dwie podlogi, ktore dzialaja BEZ karty dowodowej. | `stages._zapora_komentarza`, `stages.comment_on`, `stages.ocen_restack` |
| 3656 | `_otwarcie_formulka(zdanie)` | — | Czy zdanie zaczyna sie od zapowiedzi ruchu zamiast od samego ruchu. | `stages.ocen_restack` |
| 3698 | `sprawdz_fakty(conn, run_id, post)` | **$**(factcheck) DEAD? | Szuka faktów do komentarza, zamiast pozwolić modelowi pisać z pamięci. | — |
| 3735 | `bez_wstrzykniecia(tekst, wlasny_adres_ok)` | — | Czy w naszym tekscie nie ma sladu cudzych POLECEN. | `stages._zapora_komentarza`, `stages._zapora_notki`, `stages.bramka_kandydata`, `stages.comment_on` *(+4)* |
| 3803 | `_status_twierdzenia(c)` | — | Status twierdzenia, znormalizowany. | `stages.napraw_obalone`, `stages.zweryfikuj` |
| 3827 | `zweryfikuj(conn, run_id, tekst, kontekst)` | **$**(factcheck) | Sprawdza to, co model NAPISAŁ — nie to, czego szukał przed pisaniem. | `artykul_z_puli._napisz_i_zapisz`, `run.main`, `stages.comment_on`, `stages.napraw_obalone` *(+1)* |
| 3902 | `zweryfikuj._ma_sprawdzalny_konkret(c)` | — | Czy w twierdzeniu jest liczba — data, kwota, odsetek, rok. | `stages.zweryfikuj` |
| 3950 | `_zapora_notki(tekst)` | — | Pusty napis, gdy tekst notki przechodzi zapory. | `stages.note` |
| 3961 | `_zapora_komentarza(tekst)` | — | To samo dla komentarza — ale komentarz ma zapore o jedna wiecej. | `stages.comment_on` |
| 3970 | `_liczby_zarzutu(c)` | — | Liczby z zarzutu, znormalizowane — po nich rozpoznajemy TEN SAM fakt. | `stages._ten_sam_zarzut` |
| 3985 | `_slowa_zarzutu(c)` | — | Slowa tresciowe z samego twierdzenia — drugi sygnal tozsamosci. | `stages._ten_sam_zarzut` |
| 3997 | `_adres_zarzutu(c)` | — | — | `stages._ten_sam_zarzut` |
| 4001 | `_ten_sam_zarzut(a, b)` | — | Czy dwa zarzuty mowia o tym samym fakcie. | `stages.napraw_obalone` |
| 4045 | `napraw_obalone(conn, run_id, tekst, audyt, kontekst, min_slow, max_slow, etap, zapora)` | **$**((zmienna)) | Poprawia zdanie, ktoremu zapis przeczy. | `stages.comment_on`, `stages.note` |
| 4268 | `comment_on(conn, run_id, post, fakty)` | **$**(comment) | Komentarz do cudzego posta — do szuflady. | `run.dzien`, `run.dzien.dyskusje`, `run.dzien.komentarze` |
| 4388 | `comment_on.powtarza_otwarcie(d)` | — | — | `stages.comment_on` |
| 4483 | `fallback_card(question, evidence)` | — | Karta złożona z dowodów bez modelu — gdy synteza padnie. | `artykul_z_puli._przebieg`, `run.main` |
| 4522 | `synthesis(conn, run_id, question, evidence)` | **$**(synthesis) | Etap 6 — karta dowodowa (DeepSeek V4 Pro). | `artykul_z_puli._przebieg`, `run.main` |
| 4574 | `classify(conn, run_id, question, corpus)` | **$**(classify) | Etap 5 — klasyfikacja i wyciąg fragmentów (DeepSeek). | `artykul_z_puli._przebieg`, `run.main` |
| 4644 | `_dobierz_przegladarka(conn, run_id, brakujace, juz_mamy)` | WWW DB | Drugie podejscie do stron, ktore zwyklemu pobieraniu daly pusty szkielet. | `stages.fetch` |
| 4705 | `fetch(conn, run_id, sources)` | DB | Etap 4 — pobranie stron. | `artykul_z_puli._przebieg`, `run.main` |
| 4839 | `_host(url)` | — | — | `stages._dobierz_przegladarka`, `stages.bank_fragmentow`, `stages.discovery`, `stages.fetch` |
| 4843 | `hosty_ktore_nigdy_nie_dzialaly(conn, min_prob)` | DB | Hosty, ktore probowalismy >=2 razy i ANI RAZU sie nie udalo. | `audyt_researchu.main`, `stages.discovery` |
| 4885 | `discovery(conn, run_id, question, recent_domains, tylko_pierwotne)` | **$**(discovery) | Etap 3 — dyskoveria zrodel (DeepSeek V4 Pro + web_search dostawcy). | `artykul_z_puli._przebieg`, `run.main` |
| 5041 | `feasibility(conn, run_id, topics)` | **$**(feasibility) | Etap 2 — tani odsiew przed drogą dyskoverią (DeepSeek). | `run.main` |
| 5065 | `podsumowanie_dzialan(dni)` | — | Ile czego WYSZLO w ostatnich `dni` dniach, wobec normy z configu. | `alarm.sprawdz_wszystko`, `alarm.wolumeny` |
| 5172 | `powody_porazek(dni)` | — | Dlaczego dzialania sie NIE UDALY — pogrupowane, najczestsze pierwsze. | `alarm.sprawdz_wszystko` |
| 5212 | `_powod_przegranej(klucz_zwyciezcy, klucz_tematu)` | — | Ktory skladnik klucza sortowania ROZSTRZYGNAL, i jakimi wartosciami. | `stages.pick_topic` |
| 5228 | `_pisze_do_produkcji(sciezka)` | — | Czy ta sciezka to PRAWDZIWY katalog danych, a nie katalog testu. | `stages.zapamietaj_niewystawiony`, `stages.zapisz_przegranych` |
| 5236 | `zapisz_przegranych(przegrani, run_id)` | DB | Dopisuje do dziennika tematy, ktore NIE wygraly, z powodem przegranej. | `stages.pick_topic` |
| 5288 | `pick_topic(topics, assessments, run_id, wczesniejsze)` | — | Wybiera temat leksykograficznie wedlug dziewieciu kryteriow. | `run.main` |
| 5305 | `pick_topic.temat(a)` | — | — | `stages.pick_topic`, `stages.pick_topic.artykulowy`, `stages.pick_topic.niepowtorzony`, `stages.pick_topic.nosny` *(+3)* |
| 5309 | `pick_topic.nosny(a)` | — | Czy temat niesie KTORAKOLWIEK z dwoch rzeczy: przekonanie albo stawke. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 5319 | `pick_topic.swiezy(a)` | — | Czy tego jeszcze nie opisano gdzie indziej. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 5332 | `pick_topic.wlasny_ranking(a)` | — | Gdzie model postawil ten temat wsrod SWOICH wlasnych propozycji. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 5342 | `pick_topic.watki(a)` | — | Ile osobnych pytan niesie temat. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 5346 | `pick_topic.artykulowy(a)` | — | Czy temat ma udokumentowana historie awarii I zasieg poza jedno miejsce. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 5357 | `pick_topic.niepowtorzony(a)` | — | Czy tego tematu nie opisalismy juz pod inna nazwa. | `stages.pick_topic`, `stages.pick_topic.kolejnosc` |
| 5383 | `pick_topic.kolejnosc(a)` | — | — | `stages.pick_topic` |
| 5482 | `scout(conn, run_id, count)` | **$**(scout) | Etap 1 — skaut tematow (DeepSeek V4 Pro). | `run.main` |
| 5607 | `scout.indeksy(klucz)` | — | Indeksy z rankingu: BEZ POWTORZEN, w kolejnosci podanej przez model. | `stages.scout`, `stages.scout.wazenie` |
| 5628 | `scout.wazenie(klucz, sila)` | — | Punkty MALEJACE z pozycja na liscie. | `stages.scout` |
| 5840 | `bank_fragmentow(conn, dni)` | DB | Nieuzyte fragmenty ze wszystkich artykulow — zaplacone i nieprzeczytane. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 5881 | `bibliotekarz(conn, run_id, bank)` | **$**(bibliotekarz) | Grupuje bank po MECHANIZMIE. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 5934 | `wczytaj_bank_notek()` | — | Gotowe notki czekajace na swoj moment. | `stages.dopisz_do_banku_notek`, `stages.stan_banku_notek`, `stages.wez_z_banku_notek` |
| 5945 | `dopisz_do_banku_notek(notki)` | DEAD? | Dokłada notki do banku, pomijajac te, ktore juz tam sa. | — |
| 5971 | `wez_z_banku_notek(ile)` | DB DEAD? | Wyjmuje najstarsze niewykorzystane notki i ZNACZY je jako wyjete. | — |
| 5991 | `stan_banku_notek()` | DEAD? | Ile mamy zapasu — do wypisania przy starcie przebiegu. | — |
| 6024 | `warto_pisac(conn, run_id, card)` | **$**(warto_pisac) | Etap przed pisarzem: czy jest tu luka, ktora obcy poczuje. | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| 6071 | `warto_pisac.jest(klucz)` | — | — | `stages.warto_pisac` |
| 6171 | `zbierz_pytania(wpisy)` | DB | Wyławia z odpowiedzi czytelnikow te, ktore sa PYTANIAMI, i zapisuje je. | `run.dzien`, `run.dzien.odpowiedzi` |
| 6214 | `wczytaj_pytania()` | — | Pula pytan czytelnikow. | `stages.pytania_dla_skauta`, `stages.zbierz_pytania` |
| 6224 | `pytania_dla_skauta(ile)` | — | Najswiezsze pytania czytelnikow, gotowe do wklejenia w prompt skauta. | `stages.scout` |
| 6229 | `_to_pdf(odpowiedz, url)` | — | Czy to PDF. | `stages.fetch` |
| 6248 | `_tekst_z_pdf(dane, max_stron)` | — | Warstwa tekstowa PDF-a. | `stages.fetch` |
| 6289 | `bramka_kandydata(k)` | — | Czy z tego da sie zrobic notke. | `audyt_tematow.main`, `stages.dopisz_kandydatow` |
| 6461 | `wczytaj_indeks()` | — | Indeks kandydatow. | `alarm.bank_bez_tematow`, `stages.bank_pelny`, `stages.dopisz_kandydatow`, `stages.posortuj_bank` *(+4)* |
| 6494 | `_zapisz_indeks(indeks)` | — | Zapis ATOMOWY: najpierw plik obok, potem podmiana jednym ruchem. | `stages.dopisz_kandydatow`, `stages.posortuj_bank`, `stages.wez_kandydatow`, `stages.zwroc_kandydatow` |
| 6516 | `_stale_sygnaly(topics, pola)` | — | Ktore z pol mialy TE SAMA wartosc u WSZYSTKICH kandydatow. | `stages.pick_topic`, `stages.scout` |
| 6541 | `_precedens_ok(p)` | — | Czy ten wpis to naprawde precedens, a nie wypelniacz. | `stages.scout` |
| 6564 | `_wspolna_kotwica(a, b)` | — | Czy oba zdania mowia o tej samej NAZWIE albo tej samej LICZBIE. | `alarm.bank_bez_tematow`, `stages.dopisz_kandydatow` |
| 6578 | `_wspolna_kotwica.kotwice(t)` | — | — | `stages._wspolna_kotwica` |
| 6588 | `dopisz_kandydatow(kandydaci)` | DB | Przepuszcza kandydatow przez bramke i dokłada do indeksu. | `stages.znajdz_ciekawostki` |
| 6694 | `wez_kandydatow(ile)` | DB | Wyjmuje kandydatow gotowych do pisania i ZNACZY ich jako uzytych. | `artykul_z_puli.wybierz_fakt`, `audyt_tematow.main`, `stages.notki_dnia` |
| 6807 | `wez_kandydatow._dzielą_rzadkie(a, b)` | — | Rzadkie slowo LUZUJE PROPORCJE, ale nie liczbe wspolnych rdzeni. | `stages.wez_kandydatow` |
| 6878 | `co_zadzialalo(ile)` | — | NASZE wlasne notki z ZMIERZONYM odbiorem — material dla sedziego banku. | `audyt_tematow.main`, `stages.posortuj_bank` |
| 6943 | `co_zadzialalo._wystawiona(r)` | — | — | `stages.co_zadzialalo` |
| 6961 | `_tabela_odbioru(naj, ile)` | — | Najlepiej i najgorzej przyjete notki, gotowe do wklejenia w prompt. | `stages.co_zadzialalo` |
| 6968 | `_tabela_odbioru.punkty(r)` | — | — | `stages._tabela_odbioru` |
| 6976 | `_tabela_odbioru.wiersz(r)` | — | — | `stages._tabela_odbioru` |
| 6994 | `posortuj_bank(conn, run_id, ile)` | **$**(bank) | Ustawia bank pomyslow od najmocniejszego i wyrzuca slabe. | `stages.notki_dnia` |
| 7155 | `_termin_waznosci(dni)` | — | Kiedy ta kandydatura przestaje byc tematem. | `stages.dopisz_kandydatow` |
| 7162 | `_z_obecnej_epoki(k)` | — | Czy ta kandydatura powstala PO ostatniej zmianie tematu konta. | `stages.bank_pelny`, `stages.posortuj_bank`, `stages.wez_kandydatow` |
| 7181 | `_po_terminie(k)` | — | Czy kandydatura jest juz po swoim terminie przydatnosci. | `audyt_tematow.main`, `stages.bank_pelny`, `stages.wez_kandydatow` |
| 7203 | `bank_pelny()` | — | Czy zapas wystarczy, zeby NIE placic za nowe szukanie. | `audyt_tematow.main`, `stages.znajdz_ciekawostki` |
| 7221 | `zwroc_kandydatow(kandydaci)` | — | Oddaje do puli kandydatow, ktorych ostatecznie NIE uzyto. | `artykul_z_puli._przebieg`, `artykul_z_puli.wybierz_fakt`, `audyt_tematow.main`, `stages.notki_dnia` |
| 7263 | `stan_indeksu()` | DEAD? | Ile mamy zapasu i ile odsialismy — do wypisania przy starcie. | — |
| 7287 | `korpus_fedreg(ile_dokumentow, ile_gestych)` | DEAD? | Preambuly przepisow, w ktorych regulator ODPOWIADA na zastrzezenia. | — |
| 7380 | `kandydaci_z_fedreg(conn, run_id, dokument)` | **$**(fedreg) DEAD? | Wyciaga kandydatow z jednej preambuly i oddaje w ksztalcie indeksu. | — |

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
| 319 | `_plik()` | — | Sciezka liczona przy KAZDYM wywolaniu, nie raz przy imporcie. | `audyt_systemu.main`, `statystyki.wczytaj`, `statystyki.zapisz` |
| 330 | `zapisz(rodzaj, identyfikator, rekord, tekst)` | — | Dopisuje JEDEN pomiar. | `browser.statystyki_pozycji` |
| 374 | `wczytaj(rodzaj)` | — | Wszystkie pomiary z pliku, w kolejnosci zapisu. | `statystyki.najnowsze_per_pozycja`, `statystyki.podsumowanie` |
| 410 | `najnowsze_per_pozycja(rodzaj)` | — | {identyfikator: ostatni pomiar}. | `alarm._co_z_tego_wyszlo`, `raport_statystyk.main`, `stages.co_zadzialalo`, `statystyki.podsumowanie` |
| 435 | `podsumowanie(rodzaj)` | — | Sumy i srednie PO POZYCJACH, nie po pomiarach. | `raport_statystyk.main`, `wzajemnosc.kanaly` |
| 452 | `podsumowanie._suma_pola(pole)` | — | — | `statystyki.podsumowanie` |

---

<a id="agent-v2style-py"></a>
## `agent-v2/style.py`

Głos redakcyjny: korpus próbek i dwa profile stylu.

9 funkcji.

| line | function | markers | what it does | called by |
|---|---|---|---|---|
| 44 | `_plik_przypiec()` | — | — | `style.load_examples`, `style.wczytaj_przypiecia` |
| 52 | `_sha256(text)` | — | — | `style.load_examples` |
| 56 | `split_paragraphs(raw)` | — | Deterministyczny podział na akapity; styl końca linii nie zmienia numeracji. | `style.load_examples` |
| 63 | `bajty_kanoniczne(raw)` | — | Bajty korpusu niezależne od tego, jak git zmaterializował plik. | `style.load_examples`, `style.split_paragraphs` |
| 84 | `wczytaj_przypiecia()` | — | Przypięcia korpusu z pliku obok niego. | `style.load_examples` |
| 116 | `load_examples()` | — | Zwraca zatwierdzone fragmenty stylu albo rzuca, jeśli korpus się nie zgadza. | `stages.write` |
| 163 | `load_profiles()` | — | Profil pozytywny i negatywny stylu artykułu. | `stages.write` |
| 186 | `_z_marka(tekst)` | — | Podstawia `{marka}` w profilu stylu. | `style.load_profiles` |
| 191 | `corpus_words()` | DEAD? | Wszystkie słowa korpusu — podłoga porównuje tekst z korpusem, nie z alfabetem. | — |

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

