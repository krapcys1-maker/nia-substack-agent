
| stała | wartość | po co |
|---|---|---|
| `AGENT_DIR` | `Path(__file__).resolve().parent` | — |
| `REPO_ROOT` | `AGENT_DIR.parent` | — |
| `ENV_PATH` | `AGENT_DIR / ".env"` | — |
| `DATA_DIR` | `AGENT_DIR / "data"` | — |
| `DB_PATH` | `DATA_DIR / "agent-v2.db"` | — |
| `PROMPTS_DIR` | `AGENT_DIR / "prompts"` | — |
| `ARTICLES_DIR` | `DATA_DIR / "articles"` | — |
| `STYLE_CORPUS_DIR` | `PROMPTS_DIR / "styl"` | Korpus stylu. Przypięty hashem, bo to jedyna rzecz odróżniająca to konto od tysiąca innych — loader ma odmówić, jeśli ktoś po cichu podmieni |
| `STYLE_CORPUS` | `_korpus_stylu()` | — |
| `STYLE_PROFILES_DIR` | `REPO_ROOT / "style-profiles"` | — |
| `STYLE_PROFILE_POSITIVE` | `STYLE_PROFILES_DIR / "ARTICLE_STYLE_PROFILE_` | PROFILE STYLU SA POLEM PRESETU (`styl.profil_pozytywny`, `styl.profil_negatywny`). Do 2026-09-05 `style.load_profiles` mialo obie nazwy plik |
| `STYLE_PROFILE_NEGATIVE` | `STYLE_PROFILES_DIR / "ARTICLE_NEGATIVE_STYLE` | — |
| `STYL_WYMAGAJ_KORPUSU` | `True` | Czy pisarz artykulu ODMAWIA bez przypietego korpusu. Tak bylo zawsze i tak zostaje domyslnie; preset moze to wylaczyc (`styl.wymagaj_korpusu |
| `STYL_OPIS` | `""` | GLOS OPISANY SLOWAMI (`styl.opis`). Idzie do briefow pisarza, notki, komentarza i odpowiedzi jako `{styl_opis}` — patrz `stages._pola_wspoln |
| `PRODUKCYJNY_KATALOG_DANYCH` | `DATA_DIR` | GDZIE NAPRAWDE LEZY PRODUKCJA. Zapamietane TERAZ, przed jakimkolwiek przekierowaniem, bo po przestawieniu `DATA_DIR` nie da sie juz odtworzy |
| `ANTHROPIC_API_KEY` | `_env("ANTHROPIC_API_KEY")` | — |
| `DEEPSEEK_API_KEY` | `_env("DEEPSEEK_API_KEY")` | — |
| `OPENAI_API_KEY` | `_env("OPENAI_API_KEY")` | — |
| `IMAGE_MODEL` | `"gpt-image-1.5"` | Grafika do artykulu. Wybor NIE jest podyktowany cena: przy jednym obrazie na artykul nawet najdrozsza opcja to grosze miesiecznie, a taniej  |
| `IMAGE_SIZE` | `"1536x1024"` | — |
| `IMAGE_QUALITY` | `"high"` | — |
| `IMAGE_PRICE_USD` | `0.04` | — |
| `IMAGE_TIMEOUT_S` | `300` | — |
| `NAZWA_MARKI` | `"Your Publication"` | Konto na Substacku. Nazwa publikacji, tak jak ma ja widziec model i czytelnik. DO 2026-09-03 NIE ISTNIALA JAKO STALA. Nazwa stala wpisana w  |
| `SUBSTACK_HANDLE` | `"your-handle"` | — |
| `WYLACZ_WYKRYWANIE_AI` | `True` | Czy agent ma klikac "Wylacz wykrywanie AI" przy kazdej publikacji. WLACZONE decyzja wlasciciela z 2026-08-15. To wybor publiczny, nie ustawi |
| `DRY_RUN` | `_env("DRY_RUN", "false").lower() in {"1", "t` | — |
| `KILL_SWITCH` | `_env("KILL_SWITCH", "false").lower() in {"1"` | — |
| `NO_LIMIT` | `_env("AGENT_V2_NO_LIMIT", "0").lower() in {"` | — |
| `TRYB_SERWERA` | `_env("AGENT_V2_SERVER", "0").lower() in {"1"` | Serwer bez ekranu: zamiast podlaczac sie do Chrome'a uruchomionego przez czlowieka, agent otwiera wlasna przegladarke bez ekranu i wklada je |
| `CLAUDE` | `"claude-opus-5"` | — |
| `SONNET` | `"claude-sonnet-5"` | — |
| `FABLE_5` | `"claude-fable-5"` | PISARZ ARTYKULOW. Fable 5.1 wyszedl 1 wrzesnia 2026 i od 3 wrzesnia pisze artykuly; poprzednik zostaje pod wlasna nazwa, bo pod nia stoi cal |
| `FABLE` | `"claude-fable-5-1"` | — |
| `DEEPSEEK` | `"deepseek-v4-flash"` | — |
| `DEEPSEEK_PRO` | `"deepseek-v4-pro"` | — |
| `MODEL_FOR` | `{ "scout": DEEPSEEK_PRO, "feasibility": DEEP` | Decyzja wlasciciela 2026-08-15 zaczela od DeepSeeka poza pisaniem. Po pozniejszych testach artykuly trafily do Fable 5, notki do Opusa 5, a  |
| `DEEPSEEK_BASE_URL` | `"https://api.deepseek.com"` | — |
| `DEEPSEEK_EFFORT` | `"low"` | Głębokość rozumowania DeepSeeka na /responses. Tokeny rozumowania liczą się do sufitu wyjścia, więc przy `high` model kończy budżet na szuka |
| `CHEAP_MODE` | `_env("AGENT_V2_CHEAP", "0").lower() in {"1",` | Tryb tani: wszystko na DeepSeeku poza dyskoveria, ktora ten jawny override zostawia u Claude'a. Sluzy do testowania HYDRAULIKI — czy lancuch |
| `BEZ_TOKENOW` | `{"obraz"}` | — |
| `OBRAZ_WLACZONY` | `True` | CZY OKLADKA W OGOLE POWSTAJE. Preset wylacza ja pustym `modele.obraz`; `stages.grafika` wtedy nie wola ani briefu, ani OpenAI. Do 2026-09-05 |
| `ZAPASOWY_PISARZ` | `CLAUDE` | NA JAKI MODEL WRACA PISARZ PO AWARII SKONFIGUROWANEGO. `run.py` i `artykul_z_puli.py` mialy tu wpisane `config.CLAUDE` na sztywno, wiec zmia |
| `PRICING` | `{ CLAUDE: {"in": 5.00, "out": 25.00, "verifi` | — |
| `STAWKI_PRZED_PODWYZKA` | `{ DEEPSEEK: {"in": 0.14, "out": 0.28, "cache` | --- taryfa szczytowa DeepSeeka ----------------------------------------------- Od 2026-08-16 16:00 UTC DeepSeek wprowadza ceny szczytowe i p |
| `TARYFA_SZCZYTOWA_OD` | `"2026-08-16T16:00:00+00:00"` | — |
| `GODZINY_SZCZYTU_UTC` | `frozenset(range(1, 4)) | frozenset(range(6, ` | — |
| `MNOZNIK_SZCZYT` | `2.0` | Mnozniki wzgledem stawek wyzej, po wejsciu nowej taryfy. Szczyt to DOKLADNIE dwukrotnosc bazy, jednakowo dla wejscia, wyjscia i cache. Spraw |
| `MNOZNIK_POZA_SZCZYTEM` | `1.0` | — |
| `WEB_SEARCH_TOOL` | `{ CLAUDE: "web_search_20260209", SONNET: "we` | Filtrowanie dynamiczne (`_20260209`) jest na Opusie i Sonnecie 5. |
| `NAJNOWSZE_WYSZUKIWANIE` | `"web_search_20260209"` | Wersja narzedzia wyszukiwania dla modelu Anthropic, z galezia awaryjna. |
| `WEB_SEARCH_USD_PER_1K` | `10.00` | Wyszukiwanie po stronie Anthropic: USD za 1000 zapytań. |
| `SUFIT_PODNIESIONY_NA` | `""` | — |
| `SUFIT_PODNIESIONY_RAZY` | `2.0` | O ILE PODNOSI SIE SUFIT W DNIU PRACY PRZY WLASCICIELU. Mnoznik, nie druga liczba: sufit dzienny jest polem konfiguracji, a wpisana tu kwota  |
| `SUFIT_DZIENNY_BAZOWY` | `5.00` | SUFIT BAZOWY JEST POLEM KONFIGURACJI (`pieniadze.sufit_dzienny_usd`), a `DAILY_LIMIT_USD` — jego POCHODNA na dzis. Odwrotnie bylo zle i kosz |
| `DAILY_LIMIT_USD` | `sufit_dnia(_dzis_utc())` | Podniesienie WYGASA SAMO: jutro plik jest ten sam, a sufit z powrotem bazowy. Przeliczany po wczytaniu konfiguracji — patrz koniec pliku. |
| `TEST_LIMIT_USD_BAZA` | `3.00` | SUFIT TORU TESTOWEGO — osobny od produkcyjnego i CELOWO NIE NIESKONCZONY. Wlasciciel: „nie licz budzetu do testow, to cos osobnego". Zgoda c |
| `TEST_LIMIT_USD` | `TEST_LIMIT_USD_BAZA` | — |
| `MONTHLY_LIMIT_USD` | `40.00` | — |
| `PONOWIENIA` | `2` | Sufit na JEDEN przebieg. Działa ZAWSZE, także przy AGENT_V2_NO_LIMIT=1. „Bez limitu na budowę" miało znaczyć „nie blokuj eksperymentów", a n |
| `PONOWIENIE_ODSTEP_S` | `8` | — |
| `RUN_LIMIT_USD` | `1.60` | — |
| `TOPIC_COUNT` | `6` | --- skaut i różnorodność ---------------------------------------------------- |
| `DIVERSITY_LOOKBACK` | `5` | — |
| `DISCOVERY_MAX_RESULTS` | `10` | --- dyskoveria -------------------------------------------------------------- 10, nie 6. Odsiew przy pobieraniu jest brutalny: martwe adresy |
| `DISCOVERY_MAX_SEARCHES` | `8` | Zmierzone na jednym trudnym temacie: 31 rund -> 7 organizacji, 6 pierwotnych, $1,33  (bez limitu, przeciek) 6 rund -> 1 organizacja,  0 pier |
| `FEDREG_MAX_ZNAKOW` | `60_000` | Ponizej tylu POBRANYCH zrodel uruchamiamy druga runde dyskoverii, zanim tekst pojdzie do pisarza. Prog z danych, nie z przeczucia: artykuly, |
| `MIN_ZRODEL_DO_PISANIA` | `4` | — |
| `MIN_PRIMARY_SOURCES` | `2` | — |
| `MIN_WHY_SOURCES` | `2` | — |
| `BLOCKED_HOSTS` | `( "federalregister.gov", "regulations.gov", ` | Hosty, które serwują automatom CAPTCHA albo są płatne. Nie omijamy blokad — wykrywamy je i nie marnujemy na nie zapytań. |
| `CLASSIFY_MAX_INPUT_CHARS` | `90_000` | --- klasyfikacja ------------------------------------------------------------ |
| `CLASSIFY_MAX_EXCERPTS` | `12` | — |
| `CLASSIFY_MAX_EXCERPT_CHARS` | `700` | — |
| `CARD_MIN_CONFIRMED` | `5` | --- karta dowodowa ---------------------------------------------------------- |
| `CARD_MAX_CONFIRMED` | `8` | — |
| `CARD_MAX_UNCERTAIN` | `3` | — |
| `CARD_MAX_CONTRADICTIONS` | `3` | — |
| `CARD_MIN_NUMBERS` | `3` | — |
| `CARD_MAX_NUMBERS` | `8` | — |
| `CARD_MAX_CLAIM_CHARS` | `240` | — |
| `DLUGOSC_WG_GLEBOKOSCI` | `{ # drugi mechanizm albo ta sama rzecz w kil` | Zmierzone na dziewięciu artykułach: przy „cel 1075, zakres 950-1250" model kotwiczył się przy górnej granicy (średnia 1212). Sufit obniżony, |
| `KOTWICE_DLUGOSCI` | `{ # ZDANIE, KTORE PISARZ DOSTAJE TUZ PO CELU` | — |
| `BUDZET_ZASTRZEZEN` | `1` | Ile razy w jednym tekscie wolno powiedziec „moim zdaniem" i pochodne. Znakowanie wnioskowania jest DOBRE — recenzent wprost go chce, bo dzie |
| `NASYCENIE_OD_ILU` | `2` | Od ilu ZNANYCH ISTNIEJACYCH TEKSTOW temat uznajemy za nasycony. Skaut wymienia, co jego zdaniem juz o danym temacie napisano — i uzywamy jeg |
| `PRECEDENSOW_NA_ARTYKUL` | `2` | ILE UDOKUMENTOWANYCH AWARII ROBI Z TEMATU ARTYKUL. To jest kryterium, ktorego nie mielismy w ogole, i to przez jego brak wychodzily tematy w |
| `KOPIA_SUBSKRYBENTOW_CO_ILE_DNI` | `14` | Co ile dni ma powstawac kopia listy subskrybentow, zanim alarm zacznie o niej przypominac. Eksportu NIE DA SIE zautomatyzowac — endpoint nie |
| `ZASIEGI_ARTYKULOWE` | `("AN_INDUSTRY", "A_COUNTRY")` | KOGO WIAZE WYNIK. Drugie brakujace kryterium i drugi powod, dla ktorego tematy wychodzily mialkie. Zepsuta maszyna do glosowania to piecset  |
| `ILE_TEKSTOW_DO_POROWNANIA_FORMY` | `4` | Ile ostatnich artykulow porownuje bramka ODCISK_FORMY. |
| `SLOW_NA_BEAT` | `150` | Ile slow moze przypadac na jedno NOWE twierdzenie. Beat to zdanie, po ktorym czytelnik wierzy w cos innego niz zdanie wczesniej; powtorzenie |
| `ARTICLE_LANGUAGE` | `"English"` | Artykuł powstaje po angielsku — konto jest anglojęzyczne. |
| `CHARS_PER_TOKEN` | `3.5` | Zachowawczo, żeby sufit był raczej za duży niż za mały. Zmierzone na starym agencie: CJK 2,19x, cyrylica 1,41x; dla angielskiego 3,5 znaku n |
| `JSON_OVERHEAD_TOKENS` | `1200` | Ile tokenów zajmuje rusztowanie JSON-a, klucze i pola opisowe poza samą treścią. |
| `THINKING_HEADROOM_TOKENS` | `28000` | Myślenie na Opusie 5 jest domyślnie włączone, liczy się jak tokeny wyjściowe i NIE jest częścią kontraktu — więc sufit wyliczony z samego ko |
| `EFFORT` | `{ "scout": "medium", "discovery": "medium", ` | Głębokość myślenia. Jawnie, bo domyślne `high` na Opusie 5 potrafi podwoić rachunek za wyjście bez pytania. TO JEST POKRETLO WYLACZNIE DLA M |
| `MAX_TOKENS` | `{ # 6 tematow: tytul, pytanie, ZLAMANE PRZEK` | — |
| `NOTE_MIN_WORDS` | `33` | --- notki i komentarze ------------------------------------------------------ Zmierzone na publicznych analizach Substacka: 33-64 słowa dają |
| `NOTE_MAX_WORDS` | `64` | — |
| `DLUGOSC_NOTKI_WG_TYPU` | `{ "SPROSTOWANIE": (33, 42), # najkrótsza: je` | DLUGOSC WG TYPU NOTKI — zeby piec notek na dobe nie bylo piecioma notkami tej samej dlugosci. Reguła „nie pisz wszystkiego tej samej długośc |
| `NOTE_CANDIDATES` | `1` | Ilu kandydatow generujemy. Dawniej bylo pieciu, potem trzech; dodatkowe warianty tego samego zdania niczego nie dokladaly, a placilismy za n |
| `ILE_DZIEDZIN_NA_PRZEBIEG` | `5` | — |
| `CURIOSITY_BATCH` | `8` | — |
| `CURIOSITY_MEMORY` | `60` | Ile ostatnio zuzytych faktow pokazujemy szukajacemu jako zakaz powtorki. Bez tego to samo szukanie codziennie oddaje te same slynne osiem. |
| `PAMIEC_NOTEK` | `None` | Ile OSTATNICH WYSTAWIONYCH NOTEK bot pamieta, wybierajac material na dzis. `None` = WSZYSTKIE, jakie kiedykolwiek wyszly. To jest stan obowi |
| `MAKS_WIEK_ZRODLA_DNI` | `90` | ILE DNI MOZE MIEC ZRODLO FAKTU, KTORY TWIERDZI COS O STANIE TERAZ. Wlasciciel ustawil to sam, dwa razy. Najpierw ogolnie: „cos, co mialo sen |
| `TWIERDZI_O_TERAZ` | `( "now", "currently", "today", "these days",` | Slowa, po ktorych poznajemy, ze zdanie twierdzi cos o STANIE SWIATA TERAZ, a nie opowiada o zdarzeniu z wlasna data. Tylko takie zdania podl |
| `ZNIKA` | `( "deprecat", "retired", "retirement", "suns` | Slowa, ktore mowia, ze rzecz jest W TRAKCIE ZNIKANIA. Publikacja o szybko zmieniajacej sie dziedzinie nie ma po co opisywac czegos, co za os |
| `WZORZEC_WERSJI` | `r"\b(gpt|claude|gemini|llama|mistral|qwen|gr` | NAZWA PRODUKTU Z NUMEREM WERSJI. Wlasciciel: „nie ma mi pisac o GPT 5.0, jak jest juz 5.5". Zdanie, ktore nazywa konkretna wersje, starzeje  |
| `COMMENT_CANDIDATES` | `3` | SUFIT PROB, NIE LICZBA WYWOLAN. Do 5 wrzesnia 2026 ta stala znaczyla "napisz tylu kandydatow", i tyle wywolan szlo za kazdym razem — takze w |
| `DLUGOSCI_WYPOWIEDZI` | `( (12, 3), # jedno zdanie, najczestsze u lud` | DLUGOSC KOMENTARZA I ODPOWIEDZI losowana osobno za kazdym razem. Sam prompt tego nie zalatwi: proszony o roznorodnosc model i tak osiada w w |
| `POSTAWY_KOMENTARZA` | `{ "CIEKAWOSC": (7, ( "Say what genuinely cau` | SPOSOB OTWARCIA, losowany tak samo jak dlugosc i z tego samego powodu. Zmierzone na naszych wlasnych komentarzach: SIEDEM Z DZIEWIECIU zaczy |
| `OTWARCIA` | `( "Start with the mechanism itself, no pream` | — |
| `OTWARCIE_SPRZECIWU` | `"Start with the objection: say plainly where` | OTWARCIA, KTORYCH DANA POSTAWA NIE MOZE WYKONAC. Postawa i otwarcie byly losowane NIEZALEZNIE, wiec komentarz potrafil dostac w jednym promp |
| `OTWARCIE_KOREKTY` | `"Start by naming what the piece got right, t` | — |
| `OTWARCIA_TYLKO_DLA` | `{ OTWARCIE_SPRZECIWU: frozenset({"SPRZECIW",` | Kto MOZE dostac dane otwarcie. Postawy spoza listy go nie dostaja. |
| `COMMENTS_PER_DAY` | `4` | Sufit dzienny. Research mówi, że trzy przemyślane komentarze tygodniowo biją piętnaście uprzejmych; pierwotne 15-20 dziennie było z planu sp |
| `NOTE_FORMS` | `{ "PROSTA": ( "One tight paragraph. No line ` | Typy notek. W dniu publikacji artykułu lecą notki typu ARTYKUL z linkiem; w pozostałe dni — pozostałe typy, oparte na fragmentach, których a |
| `NOTE_FORM_MIX` | `("SCENA", "KONTRAST", "ZACZEP_I_KONKRET", "P` | — |
| `FORMY_ZAKAZANE_DLA_TYPU` | `{ "MYSL": frozenset({"LICZBA", "LISTA"}), }` | FORMY, KTORYCH DANY TYP NIE MA JAK WYPELNIC. Forma byla dotad losowana z CALEJ osemki, niezaleznie od typu i od materialu: `(dzien_roku + wy |
| `NOTE_TYPES` | `{ # MYSL — jedyny typ ZWOLNIONY z karty dowo` | — |
| `PUBLISH_TIMEZONE` | `"America/New_York"` | Strefa czasowa publikacji. Liczy sie strefa CZYTELNIKOW, nie wlasciciela — i to jest cala rzecz. Godziny w tym pliku pochodza z pomiarow na  |
| `WORST_NOTE_HOURS` | `(12, 13)` | NAJGORSZE OKNO — I TO JEST STALA EGZEKWOWANA, nie zapis ustalen. `pora_na_publikacje` odmawia publikacji w tych godzinach, wiec miedzy 12:00 |
| `BEST_NOTE_HOURS` | `(6, 7, 8)` | UWAGA: DWIE PONIZSZE STALE NIE SA UZYWANE PRZEZ ZADNA LINIE KODU. Agent nie wazy notek wedlug tych godzin ani dni — rozklada je losowo w okn |
| `BEST_NOTE_DAYS` | `("sunday", "saturday")` | — |
| `OKNO_PUBLIKACJI_ET` | `(6, 22)` | TWARDE OKNO PUBLIKACJI, w czasie CZYTELNIKOW. Agent wystawil notki o 03:57 i 04:00 UTC — czyli 23:57 i polnoc w Nowym Jorku. Tekst wrzucony, |
| `WORST_NOTE_DAYS` | `("monday", "friday")` | — |
| `NOTEK_PROMUJACYCH` | `3` | Rozkład na tydzień: pięć notek dziennie, dzień publikacji artykułu ma własny. Ile notek promuje jeden artykul i przez ile dni. Decyzja wlasc |
| `OKNO_PROMOCJI_DNI` | `7` | PO ILU DNIACH ARTYKUL PRZESTAJE BYC PROMOWANY, nawet jesli nie wybral swoich trzech notek. `artykul_do_promocji` sam nazwal ten problem w do |
| `DATA_PRZESTAWIENIA` | `""` | DZIEN, W KTORYM TO KONTO OSTATNI RAZ ZMIENILO TEMAT. Nie jest to data historyczna dla ozdoby — czyta ja `stages.wez_kandydatow` i odrzuca ka |
| `BANK_UDZIAL_ARTYKULOW` | `0.33` | Jaka czesc banku moze niesc znacznik „na artykul". Pytany po kolei „czy to unioslo by artykul", model mowi tak prawie zawsze — ta sama degen |
| `BANK_MAKS_WOLNYCH` | `20` | --- BANK POMYSLOW: BUFOR, NIE MAGAZYN -------------------------------------- Wlasciciel, 30 sierpnia: „nie moze byc tak, ze mamy za duzo tem |
| `SZUKANIE_BANKU_NA_DOBE` | `1` | ILE RAZY NA DOBE WOLNO DOBIERAC MATERIAL DO BANKU. Bylo: przy kazdym z pieciu przebiegow. Zmierzone 1 wrzesnia 2026 na produkcji: srednio 26 |
| `WYDARZENIE_WAZNE_DNI` | `2` | JAK DLUGO TO SAMO WYDARZENIE NIE OTWIERA FURTKI DRUGI RAZ. Wlasciciel: „chce napisac o tym w tym samym dniu, max dzien po". Dwie doby pokryw |
| `WYDARZENIE_PROB_MAKS` | `3` | ILE RAZY PROBUJEMY DOBRAC MATERIAL DO JEDNEGO WYDARZENIA, zanim uznamy je za zamkniete mimo braku materialu. Od 2 wrzesnia 2026 furtke zamyk |
| `BANK_MAKS_WPISOW` | `600` | TERMIN WAZNOSCI W BANKU, liczony od dnia dopisania — osobny od wieku ZRODLA. To sa dwa rozne pytania: dokument kontrolny mowi, czy fakt jest |
| `BANK_MAKS_DNI` | `7` | — |
| `NOTE_MIX_ARTICLE_DAY` | `("ARTYKUL", "ARTYKUL", "CIEKAWOSTKA", "SPROS` | MIESZANKA DNIA. Ostatnia pozycja to MYSL — notka bez zadnego dowodu. Powod jest w NOTE_TYPES przy samym typie: wszystkie pozostale wymagaja  |
| `KSZTALTY_MYSLI` | `{ "PYTANIE": ( "Ask something nobody can set` | KSZTALTY NOTKI TYPU MYSL. Losowane w kodzie i podawane jako PRZYDZIAL. Powod jest zmierzony: opis typu wymienial pytanie i obserwacje jako d |
| `NOTE_MIX_OTHER_DAY` | `("CIEKAWOSTKA", "CIEKAWOSTKA", "DYSKUSJA", "` | — |
| `NOTKI_DZIENNIE` | `len(NOTE_MIX_OTHER_DAY)` | LICZBA SLOTOW NOTEK NA DOBE — jedna dla obu rodzajow dnia. Wyprowadzona z miksu, a nie wpisana obok niego: `konfiguracja.zastosuj` ustawia j |
| `LAJKI_DZIENNIE` | `(10, 16)` | --- zachowanie spoleczne: widelki, nie stale liczby ------------------------- Stala liczba dziennie wyglada jak robot, bo czlowiek nie ma no |
| `KOMENTARZE_DZIENNIE` | `(15, 23)` | Osiemnascie komentarzy dziennie pod cudzymi tekstami to nie jest tempo czytelnika, tylko podpis bota — i kosztuje najwiecej po pisaniu, bo k |
| `FOLLOW_MIESIECZNIE` | `(10, 16)` | ZEROWANE 2026-08-23, PRZYWROCONE 2026-09-01 — BO WNIOSEK BYL FALSZYWY. Stalo tu `(0, 0)` z uzasadnieniem „Substack zdjal Follow ze stron pro |
| `SUBSKRYPCJE_MIESIECZNIE` | `(12, 20)` | — |
| `PROG_ALARMU_WOLUMENU` | `60` | Ponizej ilu procent normy uznajemy, ze cos jest zepsute, a nie po prostu chudsze. Prog jest niski celowo: budzety sa LOSOWANE z widelek i dz |
| `CICHY_DZIEN_NA_ILE` | `8` | ODBLOKOWANE decyzja wlasciciela 2026-08-19. Restack cudzej notki z wlasnym zdaniem trafia do kanalu NASZYCH obserwujacych, powiadamia autora |
| `CICHE_DNI_WLACZONE` | `True` | — |
| `CICHY_DZIEN_WYCISZA` | `("notki", "restacki")` | CO WYCISZA CICHY DZIEN — jedna lista, dwoch czytelnikow. `run.py` zeruje przydzial na te pozycje; `norma.py` nie wlicza takich dni do sredni |
| `BUDZET_NA_RODZAJ` | `{ "notki": "notka", "komentarze": "komentarz` | NAZWA W BUDZECIE -> NAZWA W DZIENNIKU. Dwie konwencje istnieja naprawde: budzet mowi „ile czego dzis wolno" (liczba mnoga), dziennik notuje  |
| `CICHY_DZIEN_WYCISZA_RODZAJE` | `tuple(BUDZET_NA_RODZAJ[k] for k in CICHY_DZI` | Wyprowadzone, NIE przepisane recznie — zeby nie dalo sie rozjechac. |
| `RESTACK_DZIENNIE` | `(1, 2)` | Zjechane z 2-4 na 1-2 (2026-08-20). Restack stawia NASZE nazwisko obok cudzego tekstu — to najmocniejszy gest w calym repertuarze i jedyny,  |
| `RESTACK_MAX_SLOW` | `40` | Dopisek do cudzej notki. Powyzej tego to juz nie dopisek, tylko wlasna notka doczepiona do czyjegos tekstu — a wtedy lepiej napisac wlasna n |
| `PRZEBIEGOW_DZIENNIE` | `5` | Pierwszy miesiac na dolnej polowie widelek. Nowe konto z jednym artykulem, ktore nagle obserwuje dwadziescia osob, wyglada dokladnie jak far |
| `GODZINY_PRZEBIEGOW_UTC` | `("11:20", "17:00", "19:20", "21:30", "23:40"` | --- HARMONOGRAM Z KONFIGURACJI, NIE Z SZABLONU ZEGARA ---------------------- Do 2026-09-05 godziny przebiegow staly WYLACZNIE w `systemd/nia |
| `ARTYKULY_TYGODNIOWO` | `1` | ILE ARTYKULOW NA TYDZIEN I W KTORE DNI. Zero wylacza sciezke artykulu: zegar artykulu nie powstaje, `artykul_z_puli.py` odmawia, promocja ni |
| `DNI_ARTYKULU` | `("Tue",)` | — |
| `GODZINA_ARTYKULU_UTC` | `"14:00"` | — |
| `PROB_PUBLIKACJI_ARTYKULU` | `3` | ILE CZASU MA PRZEBIEG. Musi zgadzac sie z `TimeoutStartSec` w pliku uslugi — to jedyne miejsce, gdzie ta sama liczba stoi dwa razy, i pilnuj |
| `PRZERWA_MIEDZY_PROBAMI_ARTYKULU_S` | `120` | — |
| `PROB_ZALEGLEGO_ARTYKULU` | `12` | ILE RAZY RUTYNA DNIA PROBUJE DOWIEZC ZALEGLY ARTYKUL, zanim przestanie. Piec przebiegow dziennie razy dwanascie prob to dwa i pol dnia dobij |
| `LIMIT_CZASU_PRZEBIEGU_S` | `9000` | — |
| `ZAPAS_CZASU_S` | `900` | Zapas na domkniecie: ostatnia publikacja, zamkniecie przebiegu, alarm. |
| `SKAUT_UDZIAL_Z_KANALOW` | `0.75` | Jaka czesc tematow skauta ma wychodzic z kanalow, ktore konto obserwuje. Decyzja wlasciciela z 30 sierpnia, po pomiarze: przed nia z kanalow |
| `ROZBIEG_DNI` | `30` | — |
| `ODSTEPY` | `{ # 45-90 MIN, nie 10-25. Zmierzone na profi` | Odstepy miedzy dzialaniami, w sekundach. Pietnascie polubien w dziewiecdziesiat sekund to nie jest czytanie i kazdy system to widzi. Odstepy |
| `ODSTEP_MIEDZY_DZIALANIAMI` | `(45, 180)` | — |
| `ZWLOKA_PRZED_NOTKAMI` | `(0, 900)` | ZWLOKA PRZED PIERWSZA NOTKA PRZEBIEGU. Bez niej pierwsza notka wychodzila zawsze kilka minut po starcie zegara, wiec piec razy dziennie o te |
| `UDZIAL_CZASU_NA_NOTKI` | `0.60` | ILE CZASU PRZEBIEGU WOLNO ZJESC SAMYM NOTKOM. Rozdzielnik dzienny nie wiedzial nic o czasie: dzielil norme tak, jakby dzialania byly natychm |
| `CZAS_DZIALANIA_S` | `240` | Ile trwa samo dzialanie poza przerwa: napisanie, sprawdzenie faktow, wystawienie i potwierdzenie u zrodla. Z realnych przebiegow. |
| `MIN_WIEK_POSTA_MIN` | `(90, 900)` | NIE KOMENTUJEMY SWIEZYCH POSTOW. Wlasciciel opisal to najlepiej: napisal notke i piec sekund pozniej ktos odpisal ogolnikowa zgoda — i to zd |
| `MIN_WIEK_NOTKI_MIN` | `(20, 90)` | NOTKA TO NIE ARTYKUL i zyje godziny, nie dni. Ten sam prog co dla artykulow oznaczal, ze pod notki wchodzilismy zawsze PO koncu rozmowy: prz |
| `KOMFORTOWO_KOMENTARZY` | `25` | ILU KOMENTARZY POD CELEM JESZCZE NIE UWAZAMY ZA TLOK. Wyszukiwarka oddawala posty ze srednio 45 komentarzami, jeden ze 126 — a komentarz sto |
| `ODSTEP_DNI_NA_PUBLIKACJE` | `4` | Ile dni odstepu przed kolejnym komentarzem pod TA SAMA publikacja. Komentarz pod kazdym kolejnym tekstem tej samej osoby to drugi najczyteln |
| `NISZA` | `""` | HASLA, KTORYMI AGENT SZUKA NOWYCH KONT. Kanal czytelnika pokazuje tylko to, co juz znamy, wiec sam z siebie nie przyprowadzi nikogo nowego — |
| `KAT_REDAKCYJNY` | `""` | KAT REDAKCYJNY — czym to konto zajmuje sie W NISZY. Do 2026-09-03 stal wpisany w DZIEWIECIU promptach, w szesciu jako „what these systems ac |
| `ILE_HASEL_NA_PRZEBIEG` | `5` | PIEC, NIE TRZY. Przy trzech haslach na przebieg i osiemnastu w puli agent ogladal jedna szosta rewiru na raz — a po zaostrzeniu reguly celow |
| `RUNDY_SZUKANIA_CELOW` | `4` | ILE RAZY SZUKAC CELOW W JEDNYM PRZEBIEGU, zanim odpuscimy. „Niech szuka, az znajdzie" bez ogranicznika znaczy „w nieskonczonosc", a kazda ru |
| `ODPOWIEDZI_POZA_LIMITEM` | `True` | Odpowiedzi POD WLASNYMI tresciami sa poza limitami dziennymi. Decyzja wlasciciela i jest sluszna: limit chroni przed wygladaniem na spamera  |
| `ODPOWIADAJ_WSZYSTKIM_DO` | `5` | Do ilu komentarzy odpowiadamy BEZ wybierania. Przy dwoch odpowiada sie obu. Przy dwustu odpowiedz pod kazdym wyglada jak maszyna — nawet gdy |
| `WYBIERAJ_POWYZEJ` | `20` | — |
| `MAX_ODPOWIEDZI_MALE` | `6` | — |
| `MAX_ODPOWIEDZI_DUZE` | `8` | — |
| `MAX_TOKENS` | `{ purpose: ceiling + THINKING_HEADROOM_TOKEN` | Zapas na myślenie dostają WSZYSTKIE etapy, nie tylko Claude'owe: modele DeepSeek v4 też rozumują, a tokeny rozumowania liczą się do sufitu w |
| `MS_PER_OUTPUT_TOKEN` | `16.08` | — |
| `TIMEOUT_MARGIN` | `1.5` | — |
| `MAX_TIMEOUT_S` | `300` | Twardy sufit na JEDNO wywolanie. Bez niego wyliczenie z sufitu tokenow dawalo 965 sekund, a przy wyszukiwaniu razy trzy — 48 MINUT. Jedno za |
| `REFUSAL_PHRASES` | `( "you have been blocked", "access denied", ` | — |
| `FETCH_TIMEOUT_S` | `30.0` | — |
| `ODSTEP_TEN_SAM_HOST_S` | `2.0` | ODSTEP MIEDZY POBRANIAMI Z TEGO SAMEGO HOSTA. Dotyczy WYLACZNIE powtorzonego hosta — rozne serwisy nie czekaja na siebie, bo to jedno zadani |
| `FETCH_MIN_CHARS` | `1500` | ILE ZNAKOW MUSI ODDAC STRONA, ZEBY LICZYC SIE JAKO ZRODLO. Bylo 400 i to bylo za malo w sposob, ktory widac dopiero na przebiegu. Zmierzone  |
| `_BEZ_PRAW_POWIEDZIANE` | `False` | --- JEDNOSTKI SYSTEMD ------------------------------------------------------ NAZWA JEDNOSTKI NALEZY DO INSTALACJI, nie do bota: kto postawi  |
| `STAN_DZIEDZINY_PYTAJ` | `True` | --- STAN DZIEDZINY: CO JEST AKTUALNE DZISIAJ ------------------------------- Model nie ma jak zauwazyc, ze fakt sie przeterminowal: jego wie |
| `STAN_DZIEDZINY_PYTANIE` | `""` | — |
| `TYTUL_SEKCJI_ZRODEL` | `"Sources"` | --- SEKCJA ZRODEL POD ARTYKULEM -------------------------------------------- Naglowek pisze KOD (`stages.save` i sciezka ratunku), a potem r |
| `NAGLOWEK_ZRODEL` | `"## " + TYTUL_SEKCJI_ZRODEL` | — |
| `KATALOG_JEDNOSTEK` | `AGENT_DIR / "systemd"` | — |
| `FETCH_USER_AGENT` | `_naglowek_klienta()` | Wartosc domyslna; przeliczana po wczytaniu konfiguracji. |
| `W_TESCIE` | `_w_darmowym_tescie()` | Jedna nazwa, dwie zapory. Wykrywanie sluzy juz nie tylko pieniadzom: darmowy test nie ma tez prawa DOPISYWAC DO PRODUKCYJNYCH DANYCH. Zmierz |
| `WOLNO_WOLAC_MODEL` | `not W_TESCIE` | Test platny albo swiadomy skrypt moze to podniesc: `config.WOLNO_WOLAC_MODEL = True`. |
| `WOLNO_TKNAC_PRODUKCYJNA_BAZE` | `not W_TESCIE` | Trzecia zapora tej samej rodziny: darmowy test nie ma prawa OTWORZYC produkcyjnej bazy. Patrz `uzyj_katalogu_danych` i `db.connect`. |
| `NAPRAWA_OBALONYCH` | `True` | --- naprawa zamiast blokady i zamiast ciecia -------------------------------- 1 wrzesnia 2026 o 19:46 poszla notka z liczba, ktora nasze wla |
| `NAPRAW_NA_PRZEBIEG` | `4` | Ile napraw najwyzej w jednym przebiegu. Kazda to dwa platne wywolania (przepisanie plus PONOWNE sprawdzenie), wiec bez sufitu zly dzien potr |
| `RUCHY_KONCOWE` | `{ "DO_SPRAWDZENIA": ( "Close by handing the ` | --- ruch koncowy i szerokosc drugiego aktu -------------------------------- Dwa artykuly napisane zaraz PO poprzedniej poprawce (jeden "Exam |
| `RUCH_KONCOWY_MIX` | `("DO_SPRAWDZENIA", "KTO_NA_TYM_STOI", "POWRO` | — |
| `ILE_PARALELI_WAGI` | `{1: 4, 2: 4, 3: 3}` | Ile paraleli w drugim akcie. Trzy wyliczone po kolei czytaja sie jak lista; jedna rozwinieta na dwa akapity czyta sie jak mysl. Chcemy obu,  |
| `OPIS_LICZBY_PARALELI` | `{ # ZERO BYLO NIEWYRAZALNE. Slownik zaczynal` | — |
| `GENERATORY` | `{ "MEASUREMENT": "A number that looks like a` | --- generatory tematow ------------------------------------------------------ Mielismy 52 DZIEDZINY, czyli odpowiedz na pytanie GDZIE szukac |
| `ILE_GENERATOROW_NA_PRZEBIEG` | `4` | — |
| `KANDYDATOW_NA_PRZEBIEG` | `25` | Ile kandydatow-jednolinijkowcow zamawiamy, zanim cokolwiek napiszemy. Nadprodukcja jest obowiazkowa: piec notek z piatki pomyslow to mediana |
| `KONFIGURACJA_PLIK` | `_konf.sciezka(AGENT_DIR)` | — |
| `_BEZ_KONFIGURACJI` | `_env("AGENT_V2_BEZ_KONFIGURACJI", "0").lower` | `AGENT_V2_BEZ_KONFIGURACJI=1` — DLA GENERATOROW DOKUMENTACJI I NARZEDZI, NIE DLA BOTA. `narzedzia/mapa_tozsamosci.py` wypisuje do repozytori |
| `DOMYSLNE_SILNIKA` | `_konf.zdjecie(sys.modules[__name__])` | NEUTRALNA BAZA SILNIKA — zdjecie stalych konta ZANIM cokolwiek je nadpisze. Od niej kompiluje sie kazdy preset: przywroc baze, naloz preset. |
| `PRESET` | `None` | --- AKTYWNY PRESET ---------------------------------------------------------- JEDEN SILNIK, JEDNA INSTANCJA NARAZ, KONTEKST ROZWIAZANY PRZED |
| `PRESET_AKTYWACJA` | `None` | — |
| `INSTANCJA` | `""` | — |
| `FETCH_USER_AGENT` | `_naglowek_klienta()` | --- STALE POCHODNE, PRZELICZANE PO WCZYTANIU KONFIGURACJI ------------------- Ten plik opisuje te pulapke przy `DB_PATH`: stala policzona RA |
| `DAILY_LIMIT_USD` | `sufit_dnia(_dzis_utc())` | Sufit na dzis: baza z konfiguracji, pomnozona tylko w dniu podniesienia. |
| `TEST_LIMIT_USD` | `min(TEST_LIMIT_USD_BAZA, DAILY_LIMIT_USD)` | Tor testowy nigdy powyzej produkcyjnego — patrz `TEST_LIMIT_USD_BAZA`. |
