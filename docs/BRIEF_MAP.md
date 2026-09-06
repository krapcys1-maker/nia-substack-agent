# Brief map — what each brief is responsible for

**Generated — do not edit by hand.** `python narzedzia/mapa_briefow.py`

The other maps answer *where things are*. This one answers **what each
brief is responsible for, and what depends on it** — specifically, for
every field a brief tells the model to return: does anything read it?

| verdict | meaning |
|---|---|
| **gate** | a gate reads it. Load-bearing: removing it changes what the bot does |
| used | some code reads it, but nothing checks its content |
| used (by name) | read through a helper that takes the field name as a string argument — verify by hand before cutting |
| **nobody** | no reader found. We pay output tokens and brief space for it |

The last verdict is a **suspicion, not a ruling**: a field can be read
through a variable this scan cannot see. Check before cutting.

## Briefs

| brief | lines | called by | model role | fields | gate | used | nobody |
|---|---|---|---|---|---|---|---|
| `bank.md` | 97 | `stages.posortuj_bank` | `bank` | 8 | 0 | 8 | 0 |
| `bibliotekarz.md` | 46 | `stages.bibliotekarz` | `bibliotekarz` | 8 | 1 | 6 | **1** |
| `cele.md` | 80 | `stages.wybierz_cele` | `cele` | 4 | 0 | 4 | 0 |
| `ciekawostki.md` | 254 | `stages.znajdz_ciekawostki` | `curiosity` | 12 | 10 | 2 | 0 |
| `dyskoveria.md` | 82 | `stages.discovery` | `discovery` | 0 | 0 | 0 | 0 |
| `fedreg.md` | 82 | `stages.kandydaci_z_fedreg` | `fedreg` | 6 | 5 | 1 | 0 |
| `forma.md` | 93 | `stages.ocen_forme` | `forma` | 14 | 8 | 6 | 0 |
| `grafika.md` | 82 | `stages.grafika` | `grafika` | 3 | 0 | 3 | 0 |
| `klasyfikacja.md` | 55 | `stages.classify` | `classify` | 5 | 1 | 4 | 0 |
| `kogo_odpowiedziec.md` | 48 | `stages.wybierz_do_odpowiedzi` | `wybor` | 5 | 0 | 5 | 0 |
| `komentarz.md` | 148 | `stages.comment_on` | `comment` | 3 | 0 | 3 | 0 |
| `mysl.md` | 135 | `stages.note` | `—` | 3 | 1 | 2 | 0 |
| `naprawa.md` | 39 | `stages.napraw_obalone` | `—` | 0 | 0 | 0 | 0 |
| `notka.md` | 165 | `stages.note` | `—` | 4 | 1 | 3 | 0 |
| `odpowiedz.md` | 131 | `stages.reply_to` | `reply` | 3 | 0 | 3 | 0 |
| `OSWIADCZENIE_AUTORSTWA.md` | 56 | **nothing** | — | 0 | — | — | — |
| `pisarz.md` | 308 | `stages.write` | `write` | 5 | 1 | 4 | 0 |
| `po_ludzku.md` | 53 | **nothing** | — | 0 | — | — | — |
| `recenzent.md` | 56 | `stages.review` | `review` | 6 | 1 | 5 | 0 |
| `restack.md` | 73 | `stages.ocen_restack` | `restack` | 4 | 3 | 1 | 0 |
| `skaut.md` | 392 | `stages.scout` | `scout` | 5 | 0 | 5 | 0 |
| `synteza.md` | 114 | `stages.synthesis` | `synthesis` | 17 | 6 | 11 | 0 |
| `warto_pisac.md` | 110 | `stages.warto_pisac` | `warto_pisac` | 13 | 0 | 13 | 0 |
| `weryfikacja.md` | 136 | `stages.zweryfikuj` | `factcheck` | 7 | 7 | 0 | 0 |
| `wykonalnosc.md` | 86 | `stages.feasibility` | `feasibility` | 7 | 1 | 6 | 0 |

## Field by field

### `bank.md`

| field | verdict | read by |
|---|---|---|
| `dlaczego_mocny` | used | `stages.posortuj_bank` |
| `id` | used | `alarm._co_z_tego_wyszlo`, `alarm.zawieszone`, `audyt_researchu.main`, `browser._artykuly_z_panelu` |
| `kod_wyrzucenia` | used | `stages.posortuj_bank` |
| `kolejnosc` | used | `stages.posortuj_bank`, `wzajemnosc.odwzajemnienie`, `wzajemnosc.opoznienia`, `wzajemnosc.raport` |
| `na_artykul` | used | `audyt_tematow.main`, `stages.artykulowy`, `stages.pick_topic`, `stages.posortuj_bank` |
| `podobne_do` | used | `audyt_tematow.main`, `stages.posortuj_bank` |
| `powod_wyrzucenia` | used | `stages.posortuj_bank` |
| `wyrzuc` | used | `stages.posortuj_bank` |

### `bibliotekarz.md`

| field | verdict | read by |
|---|---|---|
| `domain` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli.wybierz_fakt`, `audyt_researchu.main`, `db.recent_domains` |
| `id` | used | `alarm._co_z_tego_wyszlo`, `alarm.zawieszone`, `audyt_researchu.main`, `browser._artykuly_z_panelu` |
| `loners` | **nobody, unexplained** | — |
| `mechanism` | used | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| `missing` | unread, on purpose | `czego brakuje grupie — czytane przez czlowieka w logu` |
| `note` | **gate** | `stages.swiezosc_karty` |
| `role` | used | `wzajemnosc.czytelnicy`, `wzajemnosc.kanaly` |
| `why_it_travels` | unread, on purpose | `zmusza do sprawdzenia, czy mechanizm NAPRAWDE jest ten sam` |

### `cele.md`

| field | verdict | read by |
|---|---|---|
| `index` | used | `run.main`, `stages.pick_topic`, `stages.temat`, `stages.wybierz_cele` |
| `what_i_would_add` | used | `stages.wybierz_cele` |
| `why_not` | used | `stages.wybierz_cele` |
| `worth_it` | used | `stages.wybierz_cele` |

### `ciekawostki.md`

| field | verdict | read by |
|---|---|---|
| `actually` | **gate** | `stages.bramka_kandydata` |
| `consequence` | **gate** | `stages.bramka_kandydata` |
| `control_date` | **gate** | `stages.swiezosc_faktu` |
| `control_fact` | **gate** | `stages.swiezosc_faktu` |
| `control_url` | unread, on purpose | `zmusza do ZNALEZIENIA dokumentu rzadzacego, nie samego wpisania daty; kod czyta ` |
| `control_verdict` | **gate** | `stages.swiezosc_faktu` |
| `decision` | **gate** | `stages.bramka_kandydata` |
| `domain` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli.wybierz_fakt`, `audyt_researchu.main`, `db.recent_domains` |
| `fact` | **gate** | `stages.bramka_kandydata`, `stages.swiezosc_faktu` |
| `source_date` | **gate** | `stages.swiezosc_faktu` |
| `url` | **gate** | `gates.szerokosc_podstawy`, `stages.bramka_kandydata`, `stages.napraw_obalone` |
| `wrong_belief` | **gate** | `stages.bramka_kandydata` |

### `fedreg.md`

| field | verdict | read by |
|---|---|---|
| `actually` | **gate** | `stages.bramka_kandydata` |
| `consequence` | **gate** | `stages.bramka_kandydata` |
| `decision` | **gate** | `stages.bramka_kandydata` |
| `domain` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli.wybierz_fakt`, `audyt_researchu.main`, `db.recent_domains` |
| `fact` | **gate** | `stages.bramka_kandydata`, `stages.swiezosc_faktu` |
| `wrong_belief` | **gate** | `stages.bramka_kandydata` |

### `forma.md`

| field | verdict | read by |
|---|---|---|
| `already_familiar` | **gate** | `gates.uwagi_z_formy` |
| `belief` | unread, on purpose | `model musi nazwac przekonanie WLASNYMI slowami, zanim znajdzie cytat — to wymusz` |
| `first_stated` | unread, on purpose | `kotwiczy przekonanie w tekscie, zeby nie dalo sie go wymyslic` |
| `hardest_fact` | **gate** | `gates.uwagi_z_formy` |
| `object` | unread, on purpose | `wymusza konkret przy przylapaniu czytelnika` |
| `opening_claim` | **gate** | `gates.uwagi_z_formy` |
| `procedural_nearby` | **gate** | `gates.uwagi_z_formy` |
| `quote` | **gate** | `gates.uwagi_z_formy` |
| `reader_moment` | **gate** | `gates.uwagi_z_formy` |
| `same_register` | **gate** | `gates.uwagi_z_formy` |
| `summary` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli._ratuj_tekst`, `run.main` |
| `support_only` | **gate** | `gates.uwagi_z_formy` |
| `supports` | unread, on purpose | `wskazuje, ktore przekonanie wspiera zdanie — pilnuje, ze wsparcie nie jest przek` |
| `why` | used | `artykul_z_puli._napisz_i_zapisz`, `run.main`, `stages.wybierz_do_odpowiedzi` |

### `grafika.md`

| field | verdict | read by |
|---|---|---|
| `prompt` | used | `stages.grafika` |
| `subject` | used | `stages.grafika` |
| `why_this_scene` | unread, on purpose | `zmusza do wyboru sceny Z TEKSTU, nie ilustracji tematu` |

### `klasyfikacja.md`

| field | verdict | read by |
|---|---|---|
| `class` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli._przebieg`, `run.main`, `stages.classify` |
| `excerpts` | used | `artykul_z_puli._przebieg`, `run.main`, `stages.bank_fragmentow`, `stages.classify` |
| `note` | **gate** | `stages.swiezosc_karty` |
| `numbers` | used | `artykul_z_puli._przebieg`, `run.main`, `stages.classify`, `stages.fallback_card` |
| `relevance` | used | `stages.classify` |

### `kogo_odpowiedziec.md`

| field | verdict | read by |
|---|---|---|
| `index` | used | `run.main`, `stages.pick_topic`, `stages.temat`, `stages.wybierz_cele` |
| `kind` | used | `stages.reply_to`, `stages.scout`, `stages.wybierz_do_odpowiedzi` |
| `rank` | used | `stages.wybierz_do_odpowiedzi` |
| `skipped_because` | used | `stages.wybierz_do_odpowiedzi` |
| `why` | used | `artykul_z_puli._napisz_i_zapisz`, `run.main`, `stages.wybierz_do_odpowiedzi` |

### `komentarz.md`

| field | verdict | read by |
|---|---|---|
| `comment` | used | `browser._plaskie`, `browser.id_z_odpowiedzi`, `browser.ile_dzis_wystawione`, `browser.nasze_pozycje_do_pomiaru` |
| `reason_if_silent` | used | `stages.comment_on`, `stages.napisz_kandydata`, `stages.reply_to` |
| `what_it_adds` | used | `stages.comment_on`, `stages.napisz_kandydata` |

### `mysl.md`

| field | verdict | read by |
|---|---|---|
| `note` | **gate** | `stages.swiezosc_karty` |
| `why_no_note` | unread, on purpose | `wyjscie awaryjne dla pomyslu, ktory potrzebowal faktu — model ma NAZWAC brakujac` |
| `words` | unread, on purpose | `wlasna deklaracja dlugosci; prawdziwa liczy kod` |

### `notka.md`

| field | verdict | read by |
|---|---|---|
| `fact_used` | unread, on purpose | `model ma wskazac fakt, na ktorym stoi notka — zapora przed zmysleniem; MYSL tego` |
| `note` | **gate** | `stages.swiezosc_karty` |
| `source_url` | unread, on purpose | `to samo, dla zrodla` |
| `words` | unread, on purpose | `wlasna deklaracja dlugosci; prawdziwa liczy kod` |

### `odpowiedz.md`

| field | verdict | read by |
|---|---|---|
| `kind` | used | `stages.reply_to`, `stages.scout`, `stages.wybierz_do_odpowiedzi` |
| `reason_if_silent` | used | `stages.comment_on`, `stages.napisz_kandydata`, `stages.reply_to` |
| `reply` | used | `run.dzien`, `run.odpowiedzi`, `stages.reply_to` |

### `pisarz.md`

| field | verdict | read by |
|---|---|---|
| `body` | **gate** | `stages.ocen_forme`, `stages.ocen_restack` |
| `limits_paragraph_present` | used | `run.main` |
| `numbers_used` | unread, on purpose | `spis liczb uzytych w tekscie — bramka LICZBA_SPOZA_KORPUSU i tak liczy je sama` |
| `subtitle` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli._ratuj_tekst`, `kanal.posty_z_kanalu`, `kanal.szukaj_nowych` |
| `title` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli._przebieg`, `artykul_z_puli._ratuj_tekst`, `browser._artykuly_z_panelu` |

### `recenzent.md`

| field | verdict | read by |
|---|---|---|
| `class` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli._przebieg`, `run.main`, `stages.classify` |
| `summary` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli._ratuj_tekst`, `run.main` |
| `supported` | used | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| `text` | **gate** | `stages.napraw_obalone` |
| `unsupported_facts` | used | `artykul_z_puli._napisz_i_zapisz`, `run.main` |
| `why` | used | `artykul_z_puli._napisz_i_zapisz`, `run.main`, `stages.wybierz_do_odpowiedzi` |

### `restack.md`

| field | verdict | read by |
|---|---|---|
| `mechanism_named` | unread, on purpose | `zmusza do nazwania mechanizmu, zanim padnie decyzja o podaniu dalej` |
| `reason` | **gate** | `stages.ocen_restack` |
| `restack` | **gate** | `stages.ocen_restack` |
| `sentence` | **gate** | `stages.ocen_restack` |

### `skaut.md`

| field | verdict | read by |
|---|---|---|
| `least_written_about` | used (by name) | `stages.scout` |
| `most_written_about` | used (by name) | `stages.scout` |
| `ranking` | used | `stages.scout` |
| `richest` | used (by name) | `stages.scout` |
| `thinnest` | used (by name) | `stages.scout` |

### `synteza.md`

| field | verdict | read by |
|---|---|---|
| `citable_numbers` | used | `artykul_z_puli._przebieg`, `run.main`, `stages.synthesis` |
| `claim` | **gate** | `stages.napraw_obalone`, `stages.zweryfikuj` |
| `contradictions` | used (by name) | `run (para klucz-etykieta)` |
| `domain` | used | `artykul_z_puli._napisz_i_zapisz`, `artykul_z_puli.wybierz_fakt`, `audyt_researchu.main`, `db.recent_domains` |
| `evidence` | used | `audyt_researchu.main` |
| `how_it_matches` | unread, on purpose | `uzasadnienie paraleli — bez niego model dokleja dowolna dziedzine` |
| `main_mechanism` | used | `run.main` |
| `means` | used | `run.main` |
| `newest` | **gate** | `stages.swiezosc_karty` |
| `not_established` | used | `artykul_z_puli._przebieg` |
| `note` | **gate** | `stages.swiezosc_karty` |
| `oldest` | **gate** | `stages.swiezosc_karty` |
| `parallel_mechanisms` | used | `gates._korpus_pobranych`, `stages.write` |
| `source_dates` | **gate** | `stages.swiezosc_karty` |
| `url` | **gate** | `gates.szerokosc_podstawy`, `stages.bramka_kandydata`, `stages.napraw_obalone` |
| `value` | used | `run.main`, `statystyki._pozycje`, `statystyki._suma` |
| `working_thesis` | used | `artykul_z_puli._przebieg`, `run.main` |

### `warto_pisac.md`

| field | verdict | read by |
|---|---|---|
| `contradicted_belief` | used | `run.main`, `stages.warto_pisac` |
| `evidence` | used | `audyt_researchu.main` |
| `felt_number` | used (by name) | `artykul_z_puli.glebokosc_z_oceny`, `stages.warto_pisac` |
| `governed_by` | used | `stages.warto_pisac` |
| `named_decider` | used | `stages.warto_pisac` |
| `one_line_verdict` | unread, on purpose | `podsumowanie dla czlowieka czytajacego uwagi` |
| `present` | used | `artykul_z_puli._surowy`, `artykul_z_puli.glebokosc_z_oceny`, `stages.jest`, `stages.warto_pisac` |
| `second_domain` | used (by name) | `artykul_z_puli.glebokosc_z_oceny`, `stages.warto_pisac` |
| `the_belief` | used | `run.main`, `stages.warto_pisac` |
| `the_question` | used | `stages.warto_pisac` |
| `the_situation` | unread, on purpose | `wymusza konkret przy nierozstrzygnietym wyniku` |
| `unsettled_outcome` | used | `stages.warto_pisac` |
| `what_would_rescue_it` | unread, on purpose | `podpowiedz dla wlasciciela, czego szukac przy DOLOZ` |

### `weryfikacja.md`

| field | verdict | read by |
|---|---|---|
| `claim` | **gate** | `stages.napraw_obalone`, `stages.zweryfikuj` |
| `safe_to_post` | **gate** | `stages.zweryfikuj` |
| `source_date` | **gate** | `stages.swiezosc_faktu` |
| `status` | **gate** | `stages.napraw_obalone` |
| `url` | **gate** | `gates.szerokosc_podstawy`, `stages.bramka_kandydata`, `stages.napraw_obalone` |
| `verdict` | **gate** | `stages.napraw_obalone` |
| `what_the_source_says` | **gate** | `stages.napraw_obalone`, `stages.zweryfikuj` |

### `wykonalnosc.md`

| field | verdict | read by |
|---|---|---|
| `confidence` | used | `run.main`, `stages.kolejnosc`, `stages.pick_topic` |
| `depth` | used | `run.main`, `stages.kolejnosc`, `stages.pick_topic` |
| `expected_primary_sources` | used | `run.main`, `stages.kolejnosc`, `stages.pick_topic` |
| `feasible` | used | `run.main`, `stages.pick_topic` |
| `index` | used | `run.main`, `stages.pick_topic`, `stages.temat`, `stages.wybierz_cele` |
| `note` | **gate** | `stages.swiezosc_karty` |
| `parallels` | unread, on purpose | `zmusza do UZASADNIENIA oceny RICH; sama ocena jest czytana` |

## Briefs nothing calls

- `OSWIADCZENIE_AUTORSTWA.md`
- `po_ludzku.md`

A brief with no caller is not automatically dead — it can be reference
material injected into another prompt, which is what `po_ludzku.md` is.
But this is also how a brief that *should* be called stops being called
and nobody notices: that file spent weeks describing itself as injected
while its name appeared in no line of code.

