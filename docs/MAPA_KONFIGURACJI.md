> **DOKUMENT HISTORYCZNY — migawka z audytu 3 września 2026.**
>
> Wersją żywą jest [CONFIGURATION_MAP.md](CONFIGURATION_MAP.md), po angielsku.
> Ten plik zostaje nietknięty jako zapis tego, co audyt ZASTAŁ — łącznie
> z rzeczami, które zostały od tego czasu naprawione: uchwyt konta w dwóch
> miejscach, kontrola kluczy obejmująca 12 ról z 26, martwy etap `fedreg`
> niewidoczny dla testu-strażnika, sześć testów z tematem wpisanym w ciało.
>
> Migawka jest tu celowo. Dokument, który po cichu aktualizuje własne
> ustalenia, przestaje być dowodem na to, że coś było zepsute.

# Mapa konfiguracji — co da się w tym bocie przestawić, a co trzeba napisać od nowa

Ten dokument odpowiada na jedno pytanie: **ile pracy dzieli ten kod od produktu,
w którym ktoś podaje temat, źródła, klucze i podział ról, po czym uruchamia
bota u siebie.**

Nie opisuje, z czego bot jest zbudowany — to robi `agent-v2/JAK_ZBUDOWANY_JEST_BOT.md`,
generowany z kodu i pilnowany testem. Ten plik opisuje, **co się w nim rusza**.

Pełny spis funkcji, z krawędziami wywołań i znacznikami kosztu, leży osobno:
[FUNCTION_MAP.md](FUNCTION_MAP.md) — 699 funkcji w 29 modułach, generowana
z drzewa składni. Problemy napotkane po drodze:
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Co jest sprawdzone uruchomieniem, a co przeczytane

W tym projekcie obowiązuje zasada, że grep w źródle nie jest dowodem, że kod
działa. Dlatego rozdzielam to wprost.

**Sprawdzone uruchomieniem w klonie** (`<katalog repozytorium>`,
HEAD `5211e26`, Python 3.12.10, Windows 11, bez playwrighta, bez prawdziwych
kluczy):

* pełny zestaw testów — 122 pliki, **116 zdanych, 6 oblanych**;
* przyczyna każdego z sześciu oblań, potwierdzona przez usunięcie przyczyny
  i ponowne uruchomienie;
* `tests/test_kanal_platnego_wywolania.py` — mapa osiągalności 28 płatnych
  wywołań, przechodzi;
* przestawienie konfiguracji na inny temat i wymyślone konto (gałąź
  `proba-innego-tematu`, commit `60d8f17`) i trzy przebiegi na niej;
* generacja `FUNCTION_MAP.md` z drzewa składni wszystkich 23 modułów;
* import `config.py` bez żadnego klucza — przechodzi.

**Przeczytane, nie uruchomione** — i tak oznaczone w tekście:

* wszystko, co dotyczy żywej sesji Substacka, publikacji, kart zasięgu
  i kanału czytelnika. Nie mam playwrighta, nie mam sesji i nie wolno mi jej
  mieć. Te fragmenty opisuję z kodu i z dokumentacji projektu;
* zmierzone koszty jednostkowe — pochodzą z `agent-v2/JAK_DZIALA_V2.md`,
  liczone tam na bazie produkcyjnej i fakturze DeepSeeka. Sam nie zapłaciłem
  ani centa i niczego nie przeliczyłem;
* zachowanie na serwerze (systemd, Chrome na wirtualnym ekranie).

**Czego nie sprawdziłem i czego nie twierdzę.** Nie wiem, czy Substack
przyjmuje sesję przeniesioną między maszynami — kod zakłada, że nie, i buduje
wokół tego całą architekturę serwera, ale to jest cudze ustalenie, nie moje.
Nie wiem, ile z 62 funkcji dotykających przeglądarki naprawdę działa dziś
przeciw żywemu Substackowi.

---

# CZĘŚĆ 1 — INWENTARZ RÓL

26 etapów w `config.MODEL_FOR`. Kolumna „kto woła" pochodzi z drzewa składni,
nie z grepa. Koszty jednostkowe — z pomiaru produkcyjnego opisanego
w `JAK_DZIALA_V2.md` (507 wywołań, $8,73); puste znaczy „nie zmierzono osobno".

## 1.1. Łańcuch artykułu

| etap | model | prompt | sufit tok. | $ / wyw. | kto woła |
|---|---|---|---|---|---|
| `scout` | deepseek-v4-pro | `skaut.md` + `SCOUT_SYSTEM` (kod) | 31 600 | 0,018 | `stages.scout:5380` |
| `feasibility` | deepseek-v4-flash | `wykonalnosc.md` | 31 085 | 0,009 | `stages.feasibility:4937` |
| `discovery` | deepseek-v4-pro | `dyskoveria.md` | 60 000 | **0,234** | `stages.discovery:4819, :4834` |
| `classify` | deepseek-v4-flash | `klasyfikacja.md` | 32 171 | 0,004 | `stages.classify:4478` |
| `synthesis` | deepseek-v4-pro | `synteza.md` | 32 948 | 0,025 | `stages.synthesis:4426` |
| `warto_pisac` | deepseek-v4-pro | `warto_pisac.md` | 34 000 | 0,015 | `stages.warto_pisac:5942` |
| `bibliotekarz` | deepseek-v4-pro | `bibliotekarz.md` | 40 000 | — | `stages.bibliotekarz:5778` |
| `write` | **claude-fable-5-1** | `pisarz.md` + `WRITER_SYSTEM` (kod) | 37 600 | **0,426** | `stages.write:541` |
| `review` | deepseek-v4-pro | `recenzent.md` | 76 000 | 0,054 | `stages.review:216` |
| `forma` | deepseek-v4-pro | `forma.md` | 52 000 | 0,025–0,05 | `stages.ocen_forme:244` |
| `grafika` | deepseek-v4-flash | `grafika.md` | 32 000 | 0,002 | `stages.grafika:834` |
| `obraz` | **gpt-image-1.5** | — (opis z `grafika`) | bez sufitu | 0,040 | `stages.grafika:841`, przez `llm.obraz` |

Cały przebieg artykułu: **0,75–0,78 USD**.

## 1.2. Rutyna dnia

| etap | model | prompt | sufit tok. | $ / wyw. | kto woła |
|---|---|---|---|---|---|
| `cele` | deepseek-v4-flash | `cele.md` | 34 000 | 0,006 | `stages.wybierz_cele:1148` |
| `curiosity` | deepseek-v4-flash | `ciekawostki.md` | 52 000 | **0,056** | `stages.znajdz_ciekawostki:1567, :1580` |
| `bank` | deepseek-v4-flash | `bank.md` | 52 000 | — | `stages.posortuj_bank:6892` |
| `wybor` | deepseek-v4-pro | `kogo_odpowiedziec.md` | 34 000 | — | `stages.wybierz_do_odpowiedzi:658`, `artykul_z_puli.temat_z_faktu:122` |
| `note` | **claude-opus-5** | `notka.md` + `NOTE_SYSTEM` (kod) | 37 314 | 0,086 | `stages.note:2472` — **etap ze zmiennej** |
| `note_tani` | deepseek-v4-pro | jw. | 37 314 | 0,010 | jw., notki parzyste/nieparzyste na zmianę |
| `factcheck` | deepseek-v4-flash | `weryfikacja.md` | 52 000 | 0,007 | `stages.zweryfikuj:3726` |
| `comment` | deepseek-v4-pro | `komentarz.md` | 37 371 | 0,006 | `stages.comment_on:4236` |
| `reply` | deepseek-v4-pro | `odpowiedz.md` | 37 371 | 0,005 | `stages.reply_to:704` |
| `restack` | deepseek-v4-pro | `restack.md` | 31 000 | 0,003 | `stages.ocen_restack:3466` |
| `naprawa` | **claude-opus-5** | `naprawa.md` | 37 314 | — | `stages.napraw_obalone:4008` — **etap ze zmiennej** |
| `naprawa_komentarza` | deepseek-v4-pro | jw. | 37 371 | — | jw. |
| `aktualne_modele` | deepseek-v4-flash | prompt w kodzie | 44 000 | — | `aktualne_modele.pobierz:115` |

## 1.3. Dwa etapy martwe

Zlecenie mówiło o jednym udokumentowanym martwym etapie. Są **dwa**.

| etap | model | funkcja | stan |
|---|---|---|---|
| `factcheck` (drugie wejście) | deepseek-v4-flash | `stages.sprawdz_fakty:3581` | udokumentowany; zero wywołań w całym repozytorium |
| **`fedreg`** | deepseek-v4-flash | `stages.kandydaci_z_fedreg:7205` | **nieudokumentowany**; wołany wyłącznie z `tests/platne/` |

`sprawdz_fakty` jest wypisany w `tests/test_kanal_platnego_wywolania.py`
w zamkniętej liście `BEZ_WOLAJACYCH` — i to jest w porządku, tak ma być.

`fedreg` **nie jest**, a mimo to nie ma ani jednego wołającego w kodzie
produkcyjnym. Test-strażnik go nie widzi, bo sprawdza dekorator kanału
**przed** sprawdzeniem, czy ktoś funkcję woła (`werdykt()`, linie 279–285):
funkcja z `@_na_kanal("bank")` i zerem wołających raportuje się jako
`KANAL:bank`, czyli zdrowa. Razem z nią martwe są `stages.korpus_fedreg:7129`
i cały plik `prompts/fedreg.md`.

Skutek dla produktu: **`config.MODEL_FOR["fedreg"]` jest polem konfiguracji,
które niczym nie steruje.** Szczegóły i propozycja naprawy —
[TROUBLESHOOTING.md, pozycja 5](TROUBLESHOOTING.md).

## 1.4. Co jeszcze trzeba wiedzieć o rolach

**Etapy nie są w relacji jeden-do-jednego z funkcjami.** Pięć etapów wybiera się
przez zmienną, nie po napisie: `note`/`note_tani` (dwaj pisarze notek na zmianę),
`naprawa`/`naprawa_komentarza` (naprawa wraca do modelu, który pisał tekst)
i `obraz` (osobna droga `llm.obraz`). Statyczne szukanie napisu `"note"`
w źródle **nie znajdzie ich wywołania**.

**Sufit tokenów jest liczony, nie wpisany.** `config.MAX_TOKENS` powstaje
z `_tokens_for(...)` i jest potem podnoszony w całości o
`THINKING_HEADROOM_TOKENS = 28 000` — bo tokeny rozumowania liczą się do sufitu
wyjścia także u DeepSeeka. Wartość w kodzie przy `"fedreg": 8000` daje
w rzeczywistości 36 000. Kto zmieni ten zapas, przestawi wszystkie 25 sufitów
naraz.

**`config.EFFORT` działa dla jednego etapu z sześciu.** Reszta chodzi na
DeepSeeku, który tego pokrętła nie czyta. Bot mówi to sam w logu — widziałem
to na własnym przebiegu:

```
[effort] scout=medium NIE MA SKUTKU — etap chodzi na deepseek-v4-pro,
a to pokretlo dziala tylko na modelach Claude
```

**Nie każdy prompt to plik.** Obok 27 plików `prompts/*.md` w `stages.py` stoją
**22 komunikaty systemowe jako stałe pythonowe** (`SCOUT_SYSTEM`,
`WRITER_SYSTEM`, `NOTE_SYSTEM`…). Nie są czytane z dysku i nie da się ich
podmienić bez edycji kodu. To ma znaczenie w części 2.

Z 27 plików promptów **cztery nie są czytane przez żaden kod**
(`po_ludzku.md`, `SKAD_BRAC.md`, `ROZWOJ_KONTA.md`,
`ZASADY_NOTEK_I_KOMENTARZY.md`), a piąty — `OSWIADCZENIE_AUTORSTWA.md` — jest czytany
wyłącznie przez funkcję, której nikt nie woła. Żywych promptów jest **21**,
nie 27.

---

# CZĘŚĆ 2 — CO JEST PRZYKLEJONE DO TEGO KONTA

Podział kolumny „rodzaj pracy":

* **KONFIG** — zmiana wartości w `config.py`. Minuty.
* **TEKST** — przepisanie prozy po angielsku, z sensem. Godziny.
* **KOD** — trzeba tknąć logikę albo strukturę. Dzień i więcej.

## 2.1. Tożsamość konta

| co | gdzie | rodzaj |
|---|---|---|
| uchwyt Substacka | `config.py:84` `SUBSTACK_HANDLE = "your-handle"` | KONFIG |
| **drugi, niezależny egzemplarz tego samego uchwytu** | `browser.py:789` `PROFIL_HANDLE = "your-handle"` | KOD |
| dwa adresy panelu wpisane na sztywno | `browser.py:751-752` | KOD |
| user-agent z nazwą marki | `config.py:2248` `FETCH_USER_AGENT` | KONFIG |
| nazwa marki w komunikacie pisarza | `stages.py:387` `WRITER_SYSTEM` | KOD |
| nazwa marki w komunikacie skauta | `stages.py:114` `SCOUT_SYSTEM` | KOD |
| nazwa marki w 9 plikach promptów | `prompts/{skaut,pisarz,notka,komentarz,cele,ciekawostki,bank,odpowiedz,warto_pisac}.md` | TEKST |
| nazwa marki w obu profilach stylu | `style-profiles/ARTICLE_*_STYLE_PROFILE_V1.md` | TEKST |
| uchwyt wpisany w **test** | `tests/test_kto_nas_czyta.py` | KOD |

**To jest wada, nie ciekawostka.** Uchwyt konta stoi w dwóch niezależnych
miejscach w kodzie i jest używany w 11 miejscach przez `PROFIL_HANDLE`
i w 16 przez `config.SUBSTACK_HANDLE`. Zmiana tylko `config.py` daje bota,
który publikuje na jednym koncie, a czyta profil drugiego. **Sprawdzone:**
zmieniłem oba i dopiero wtedy przestały pojawiać się stare adresy.

## 2.2. Temat

| co | gdzie | ile tego | rodzaj |
|---|---|---|---|
| hasła szukania celów do komentowania | `config.py:2117` `HASLA_SZUKANIA` | 24 hasła, wszystkie o AI | KONFIG |
| siatka dziedzin ciekawostek | `config.py:946` `DZIEDZINY_CIEKAWOSTEK` | **46 opisów po angielsku** | TEKST |
| wzorce ciekawostek | `config.py:2568` `GENERATORY` | 14 wzorców, **12 neutralnych tematycznie**, 2 o AI (`SEEMING`, `UNBIDDEN`) | TEKST (2 z 14) |
| kanały YouTube jako źródło tematów | `korpus_kanalow.py:36` `KANALY` | 13 kanałów o AI | KONFIG |
| odsiew nagłówków z tych kanałów | `korpus_kanalow.py:71` `OPRAWA`, `:86` `NIE_TEMAT` | wyrażenia regularne pod tytuły kanałów AI | TEKST |
| zdania „to jest pismo o AI" w promptach | 14 plików `prompts/*.md`, ~30 linii | patrz niżej | TEKST |
| to samo w komunikatach systemowych | `SCOUT_SYSTEM`, `CURIOSITY_SYSTEM`, `BANK_SYSTEM`, `FEDREG_SYSTEM` | 4 z 22 | KOD |
| kategoria odrzucenia `NOT_AI` | `prompts/bank.md:69` | jedna z etykiet bramki banku | TEKST |

Dokładne linie z tematem wpisanym wprost:

```
prompts/skaut.md:1,2,6,17,117,303,536      prompts/pisarz.md:2,16,17,40
prompts/ciekawostki.md:8,12,384            prompts/notka.md:1,2,19,28
prompts/komentarz.md:1,36,55,203           prompts/cele.md:7,25
prompts/bank.md:4,69,72                    prompts/bibliotekarz.md:1,30
prompts/restack.md:21                      prompts/grafika.md:30
prompts/synteza.md:65                      prompts/weryfikacja.md:49,95
prompts/dyskoveria.md:79                   prompts/fedreg.md:88  (etap martwy)
```

**Zmierzone na gałęzi `proba-innego-tematu`.** Przestawiłem hasła, dziedziny
i kanały z AI na kolej. Skutek:

* `artykul_z_puli.py` przeszedł dziedziny i wzorce z **nowym tematem** bez
  jednej zmiany w kodzie — to znaczy, że `DZIEDZINY_CIEKAWOSTEK` i `GENERATORY`
  są prawdziwymi pokrętłami;
* dwa wymyślone kanały YouTube oddały `HTTP 404` i bot **zdegradował się
  łagodnie** („0 filmow z 2 kanalow -> 0 tematow"), zamiast się wywrócić.
  Podmiana listy kanałów jest bezpieczna;
* **cztery testy oblały się od samej zmiany tematu** — patrz 2.5.

## 2.3. Styl i głos

| co | gdzie | rodzaj |
|---|---|---|
| korpus stylu, 226 akapitów | `prompts/styl/article_style_samples_v1.txt` | — |
| **skrót SHA-256 korpusu** | `config.py:46` `STYLE_CORPUS_SHA256` | KONFIG |
| pięć przypiętych akapitów: numer + skrót | `style.py:26` `APPROVED_EXAMPLES` | KOD |
| dwa profile stylu | `style-profiles/ARTICLE_STYLE_PROFILE_V1.md` i `..._NEGATIVE_...` | TEKST |
| zakazane słownictwo (18 słów) | `prompts/{komentarz,notka,odpowiedz,po_ludzku}.md`, sekcja „Banned vocabulary" | TEKST |
| zakazane otwarcia, zastrzeżenia, niby-źródła | `gates.py:53-95`, wyrażenia regularne po angielsku | KOD |

**Dobra wiadomość, której się nie spodziewałem: korpus stylu NIE jest o AI.**
To proza w rodzaju felietonu ekonomicznego — o szpiegostwie przemysłowym, przędzeniu
jedwabiu, tajemnicach handlowych. Uczy **ruchu retorycznego**, nie tematu.
Przy zmianie niszy można go zostawić w całości.

**Zła wiadomość: jest zabetonowany podwójnie.** Loader odmawia pracy, gdy
skrót się nie zgadza, a poza tym pięć konkretnych akapitów jest przypiętych po
**numerze porządkowym i skrócie treści**. Dopisanie jednego akapitu na początku
przesuwa numerację i zatrzymuje pisarza. Historia zapisana w `style.py` mówi,
że to już raz kosztowało opłacony research (przebieg 13, 18 sierpnia, FAILED
na `write`).

Zakazane słownictwo jest **neutralne tematycznie** — to lista typowych tików
modeli językowych (`delve`, `moreover`, `tapestry`…). Zostaje bez zmian.

## 2.4. Język

`config.ARTICLE_LANGUAGE = "English"` **jest prawdziwym pokrętłem, ale tylko dla
czterech etapów**: trafia jako pole do `pisarz.md`, `notka.md`, `komentarz.md`
i `odpowiedz.md` (`stages.py:521, 691, 2420, 4228`).

Nie steruje niczym innym. Angielski jest wpisany osobno w:

* `SCOUT_SYSTEM` — „English-language Substack" (`stages.py:114`) — KOD;
* kontekście przeglądarki — `locale="en-US"` (`browser.py:572`) — KOD;
* wszystkich 21 żywych promptach — są napisane po angielsku — TEKST;
* wyrażeniach regularnych bramek w `gates.py` — łapią angielskie frazy — KOD;
* etykiecie ciszy `wrong_language` w `stages.py:3571` — bot milczy pod postami
  w obcym języku, a „obcy" znaczy „nie ten, w którym piszemy".

**Wniosek.** Przestawienie `ARTICLE_LANGUAGE` na „Polish" — zrobiłem to na
gałęzi próbnej — nie wywołuje błędu, ale daje bota, który dostaje instrukcje po
angielsku, ma bramki łapiące angielskie frazy i pisze po polsku. To jest
konfiguracja **połowiczna**: użyteczna do testu, nie do produkcji.

## 2.5. Cztery testy, które oblewają się od samej zmiany tematu

To najtwardszy dowód, jak głęboko temat siedzi. Na gałęzi `proba-innego-tematu`
zestaw dał **114 zdanych, 8 oblanych** wobec 116/6 na `main`. Cztery nowe:

| test | asercja | co z niej wynika |
|---|---|---|
| `test_szukanie_celow` | „kazde haslo dotyczy AI" — każde hasło musi zawierać jeden z 11 znaczników (`ai`, `model`, `algorithm`, `llm`, `agent`…) | temat jest **wymuszony testem**, nie tylko wartością |
| `test_szukanie_celow` | `len(hasla) > 18` oraz pokrycie trzech obszarów: praca i ludzie, prawo i władza, pieniądze i sprzęt | konfigurator musi wymusić **minimum 19 haseł w trzech obszarach** |
| `test_generatory` | `GENERATORY × DZIEDZINY_CIEKAWOSTEK >= 400` komórek | przy 14 wzorcach trzeba **co najmniej 29 dziedzin**; ja dałem 10 i wyszło 140 |
| `test_kto_nas_czyta` | uchwyt `your-handle` wpisany w ciało testu jako „my" | test **nie da się przenieść** bez edycji |
| `test_dokumentacja_zywa` | wygenerowana dokumentacja musi zgadzać się z kodem | po każdej zmianie konfiguracji trzeba puścić `dokumentacja-zrodla/sklej.py` |

Ostatni nie jest wadą — jest cechą i dobrą. Ale znaczy, że **przebudowa
dokumentacji jest obowiązkowym krokiem konfiguracji**, nie opcją.

## 2.6. Wolumeny, rytm i zasady publikowania

Te są w całości konfigurowalne i **żadne nie wymaga tknięcia kodu**:

| co | gdzie |
|---|---|
| 5 notek, 15–23 komentarze, 10–16 polubień, 1–2 restacki dziennie | `config.py` `NOTE_*`, `KOMENTARZE_DZIENNIE`, `LAJKI_DZIENNIE`, `RESTACK_DZIENNIE` |
| 10–16 obserwacji i 12–20 subskrypcji miesięcznie | `FOLLOW_MIESIECZNIE`, `SUBSKRYPCJE_MIESIECZNIE` |
| pięć przebiegów dziennie i ich godziny | `PRZEBIEGOW_DZIENNIE` + `systemd/nia-agent.timer` |
| odstępy między działaniami (45–90 min między notkami, 5–15 min między komentarzami) | `ODSTEPY` |
| okno publikacji 6:00–22:00 czasu czytelnika, martwa godzina 12–14 | `OKNO_PUBLIKACJI_ET`, `WORST_NOTE_HOURS`, `PUBLISH_TIMEZONE` |
| ciche dni — średnio jeden na osiem | `CICHY_DZIEN_NA_ILE`, `CICHE_DNI_WLACZONE` |
| sufit dzienny 5–10 USD, miesięczny **40 USD**, na przebieg 1,60 USD | `DAILY_LIMIT_USD`, `MONTHLY_LIMIT_USD`, `RUN_LIMIT_USD` |
| 3 notki promujące artykuł, okno 7 dni | `NOTEK_PROMUJACYCH`, `OKNO_PROMOCJI_DNI` |
| miks form i typów notek, ruchy końcowe artykułu | `NOTE_FORMS`, `NOTE_TYPES`, `NOTE_MIX_*`, `RUCHY_KONCOWE` |
| długości: artykuł zależnie od głębokości tematu (RICH 900–1250, SINGLE 480–820), notka 33–64 | `DLUGOSC_WG_GLEBOKOSCI`, `NOTE_MIN_WORDS`, `NOTE_MAX_WORDS` |

`PUBLISH_TIMEZONE = "America/New_York"` jest strefą **czytelnika**, nie serwera.
Przy innej publiczności to jedna z pierwszych rzeczy do zmiany, i jest to
zwykłe pole.

---

# CZĘŚĆ 3 — KLUCZE I USŁUGI ZEWNĘTRZNE

## 3.1. Pełna lista zmiennych środowiskowych

Wyprowadzona z kodu (`_env(`, `os.environ.get(` w `agent-v2/*.py`, bez testów
i archiwum), **nie z `.env.example`** — ten plik jest nieaktualny i opisuje
poprzedniego agenta (patrz [TROUBLESHOOTING.md, pozycja 2](TROUBLESHOOTING.md)).

| zmienna | do czego | co się dzieje przy braku |
|---|---|---|
| `DEEPSEEK_API_KEY` | **21 etapów z 26** | `PreflightFailed: brak DEEPSEEK_API_KEY` — ale **tylko dla `deepseek-v4-flash`**; etapy na `deepseek-v4-pro` idą do sieci i padają na HTTP |
| `ANTHROPIC_API_KEY` | `note`, `naprawa` (Opus), `write` (Fable) | `PreflightFailed` dla Opusa; **Fable nie jest sprawdzany** |
| `OPENAI_API_KEY` | wyłącznie okładka (`obraz`) | `PreflightFailed`; artykuł wychodzi bez okładki, przebieg **nie pada** |
| `DRY_RUN` | blokuje wywołania modeli **i przeglądarkę** | domyślnie `false` |
| `KILL_SWITCH` | twarde zatrzymanie | domyślnie `false` |
| `AGENT_V2_SERVER` | serwer bez ekranu — własna przeglądarka + zapisana sesja | domyślnie `0`; ustawiane przez wszystkie trzy jednostki systemd |
| `AGENT_V2_CHEAP` | wszystko na DeepSeeku poza dyskowerią — do testów hydrauliki | domyślnie `0` |
| `AGENT_V2_NO_LIMIT` | zdejmuje sufit dzienny i miesięczny (**nie na przebieg**) | domyślnie `0` |
| `AGENT_V2_WRITER` | podmiana samego pisarza do porównań A/B | brak podmiany |
| `AGENT_V2_TRYB` | `produkcja` / `test` — wybór toru bazy (`db.py:231`) | domyślnie `produkcja` |
| `ALARM_EMAIL_TO`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | jedyny kanał, którym bot mówi „stało się źle" | **degradacja cicha** — potwierdzone: `[alarm NIEWYSLANY — brak konfiguracji]` w logu i nic więcej |

**Dziura w kontroli kluczy, sprawdzona w kodzie.** `llm.py:74-79` porównuje
identyfikator modelu, nie dostawcę. `claude-fable-5-1` (artykuł) i
`deepseek-v4-pro` (11 etapów, w tym `comment`, `reply`, `discovery`)
**nie mają kontroli wstępnej** — brak klucza wychodzi dopiero jako błąd HTTP.

## 3.2. Usługi

| usługa | punkt końcowy | do czego | wymagana? |
|---|---|---|---|
| DeepSeek | `https://api.deepseek.com/chat/completions` i `/responses` | 21 etapów; `/responses` daje wyszukiwanie po stronie serwera dla `discovery` i `curiosity` | **tak** |
| Anthropic | SDK `anthropic` | notki (Opus), artykuł (Fable), naprawa | **tak** |
| OpenAI | `https://api.openai.com/v1/images/generations` | wyłącznie okładka, `gpt-image-1.5` | nie — artykuł wychodzi bez niej |
| YouTube RSS | `https://www.youtube.com/feeds/videos.xml?channel_id=…` | 13 kanałów jako źródło tematów; **bez klucza i bez ściany zgody** | nie — degradacja do 0 tematów, potwierdzona |
| Federal Register | `korpus_fedreg` | tańsze źródło kandydatów | **etap martwy** — patrz 1.3 |
| SMTP | dowolny; domyślnie Gmail | alarmy do właściciela | nie — cicha degradacja |
| Substack | ~30 punktów `/api/v1/*` + Playwright | wszystko, co widoczne publicznie | **tak, i nie da się obejść** |

## 3.3. Sesja Substacka — jedyne miejsce, gdzie produkt zawsze potrzebuje człowieka

To jest pierwsza rzecz, o którą rozbije się każdy, kto to u siebie odpali.
**Opisane z kodu; nie uruchamiałem tego i nie mogłem.**

### Czym jest

Plik `agent-v2/data/storage-state.json` — zrzut stanu przeglądarki w formacie
Playwrighta. Liczy się w nim **jedno ciasteczko**: `substack.sid`
(`browser.py:36`). Reszta to obudowa.

Nie ma tu żadnego klucza API. Substack nie daje API do publikowania. Bot **jest
zalogowanym użytkownikiem** i wszystko robi jako on.

### Jak powstaje

Trzy kroki, z czego jeden musi wykonać człowiek:

1. Człowiek uruchamia Chrome'a z portem debugowania (`--remote-debugging-port=9222`)
   i **loguje się na Substacka własnoręcznie**.
2. `python agent-v2/browser.py sesja` — podłącza się do tego Chrome'a przez CDP,
   otwiera `substack.com/home`, sprawdza, czy widzi zalogowany widok, i zapisuje
   `context.storage_state()` do pliku (`browser.py:594-620`).
3. Plik trafia na serwer.

Droga automatyczna **istnieje i jest odradzona w samym kodzie**: `browser.py`
ma polecenie `zaloguj` z komentarzem „stara droga, zapętla CAPTCHĘ — nie
używać" (`browser.py:4894`).

### Dlaczego musi powstać na maszynie, na której bot chodzi

Ostrożnie: to jest **wniosek z architektury kodu, nie mój pomiar**.

Kod nie zakłada wprost, że sesja jest przywiązana do adresu IP — przeciwnie,
`browser.sprawdz_serwer()` istnieje po to, żeby to pytanie rozstrzygnąć,
i komunikat mówi: „jeśli Substack odrzuca sesję z innego adresu, cała droga
przez przeglądarkę wymaga przemyślenia od nowa".

Twarde ustalenie jest inne i mocniejsze. `browser.py:540-556`:

> Publikacja przez prawdziwego Chrome'a kończy się kodem 200, a przez
> bezgłowego Chromium notka po prostu nie powstaje. Cloudflare rozpoznaje
> tryb bezgłowy po odcisku przeglądarki.

Dlatego na serwerze **chodzi prawdziwy Chrome na wirtualnym ekranie**, jako
usługa `nia-chrome`, i właściciel **zalogował się w nim własnoręcznie**. Bot
podłącza się do niego przez CDP (`connect_over_cdp`), a plik sesji jest drogą
zapasową, gdy tego Chrome'a nie ma.

Czyli: nie „sesja jest przywiązana do maszyny", tylko **przeglądarka, w której
sesja żyje, musi być prawdziwa i stać tam, gdzie bot**. Skutek praktyczny jest
ten sam: człowiek musi raz usiąść przy serwerze (albo przy jego pulpicie
zdalnym) i się zalogować.

### Ile żyje i co ją unieważnia

* **Długość życia** czyta się z pola `expires` ciasteczka
  (`browser.dni_do_wygasniecia`). Kod nie zakłada żadnej stałej liczby dni —
  pyta plik.
* **Sama się przedłuża.** Po każdej pracy bot zapisuje `storage_state` na nowo:
  „Substack odświeża ciasteczko przy aktywności, więc regularne używanie konta
  samo przesuwa datę ważności" (`browser.py:782-784`).
* **Unieważnia ją**: wylogowanie się gdziekolwiek, zmiana hasła, wygaśnięcie
  ciasteczka, a przy drodze bezgłowej — rozpoznanie przez Cloudflare.

### Co się dzieje, gdy jej zabraknie

Sprawdzone uruchomieniem. Ścieżka dnia **staje natychmiast, przed jakimkolwiek
wydatkiem**:

```
== przebieg 1 ==
  [budżet dnia — rozbieg] notki=5 lajki=10 komentarze=18 ...
== koszt przebiegu: $0.0000 w 0 wywołaniach ==
Brak sesji Substacka.
Uruchom Chrome z portem debugowania, zaloguj się i wykonaj:
  python agent-v2/browser.py sesja
```

To jest dobre zachowanie i warto je zachować w produkcie: `browser.wymagaj_sesji()`
stoi **przed** wszystkim, co kosztuje.

Osobno `alarm.py` — uruchamiany codziennie o 07:00 UTC — ostrzega właściciela
mailem, gdy sesji brakuje, gdy wygasła, albo gdy zostało jej mniej niż
`browser.OSTRZEGAJ_PONIZEJ_DNI` dni. Ten alarm **też potwierdziłem
uruchomieniem** (bez SMTP wypisuje `[alarm NIEWYSLANY — brak konfiguracji]`).

### Wniosek dla produktu

Konfigurator nie zdejmie tego kroku. Każda instalacja wymaga:

1. maszyny z ekranem (choćby wirtualnym) i prawdziwym Chrome'em,
2. **jednorazowego ręcznego zalogowania przez człowieka**,
3. mechanizmu odnawiania, gdy sesja padnie mimo wszystko.

Można to opakować w kreator („otwórz przeglądarkę, zaloguj się, wróć tutaj"),
ale nie da się tego zautomatyzować bez łamania zabezpieczeń Substacka.

---

# CZĘŚĆ 4 — CZEGO NIE DA SIĘ SKONFIGUROWAĆ

## 4.1. Ile z tego bota jest uniwersalne — liczby

Zmierzone na drzewie składni (`narzedzia/mapa_funkcji.py`):

| warstwa | funkcji | co to znaczy |
|---|---|---|
| **wrośnięte w Substacka** | **62** z 519 | dotykają `page.*`, `context.*`, `browser.*` |
| — z tego w `browser.py` | 44 z 97 | |
| — w `run.py` | 10 | orkiestracja dnia woła przeglądarkę wprost |
| — w `kanal.py` | 3 | kanał czytelnika |
| **łańcuch redakcyjny** | 155 w `stages.py` | 23 płatne; platformy nie dotyka **ani jedna** poza `stages.grafika` |
| **księgowość i pomiar** | ~90 (`db`, `llm`, `norma`, `statystyki`, `wzajemnosc`, `raport_statystyk`) | zależne od Substacka tylko przez kształt danych wejściowych |
| **konfiguracja i bramki** | 48 (`config`, `gates`, `bramki`) | zależne od **języka**, nie od platformy |

**Odpowiedź wprost.** Ten bot to w przybliżeniu:

* **~55% uniwersalnej maszyny redakcyjnej** — łańcuch od pomysłu przez research,
  kartę dowodową, bramki, pisanie, recenzję po księgowanie kosztów. To działa
  dla dowolnego tematu i dowolnej platformy.
* **~25% „Substack"** — publikacja, potwierdzanie, kanał, statystyki,
  subskrybenci, restacki.
* **~15% „po angielsku"** — prompty, bramki regularne, korpus stylu.
* **~5% „o AI"** — dziedziny, hasła, kanały, zdania w promptach.

Kolejność jest zaskakująca i ważna: **temat jest najtańszy do zmiany, platforma
najdroższa, a język siedzi pośrodku i jest najczęściej niedoceniany.**

## 4.2. Substack — co znaczy inna platforma

`browser.py` ma 5131 wierszy, ale **41% z tego to komentarze i docstringi**.
Realny kod to **~2470 wierszy**. To zmienia skalę problemu: nie „230 KB do
przepisania", tylko „dwa i pół tysiąca linii Playwrighta i wywołań HTTP".

Nie da się tego wyjąć do konfiguracji, bo wrośnięte jest **znaczenie**, nie
adresy:

| co | ile | dlaczego to nie jest pole konfiguracji |
|---|---|---|
| punkty końcowe `/api/v1/*` | ~30 różnych wzorców | każdy ma własny kształt odpowiedzi, rozpakowywany osobno |
| `substack.com` w kodzie | 44 wystąpienia | |
| selektory Playwrighta | 57 (26 `get_by_role`, 22 `locator`, 4 `get_by_text`) | kompozytor notki, edytor artykułu, pole komentarza |
| **potwierdzanie publikacji** | **7 osobnych funkcji** | `potwierdz_notke`, `potwierdz_artykul`, `potwierdz_komentarz`, `potwierdz_odpowiedz`, `potwierdz_polubienie`, `potwierdz_obserwacje`, `potwierdz_adres_artykulu` |
| karty zasięgu | `note_stats/c-`, `note_stats/p-`, `publication/stats/visitor_sources`, `publication/stats/growth/sources` | **cztery różne kształty liczb**, każdy rozpakowywany osobno |
| kanał czytelnika | `kanal.py`, ~10 funkcji | „skąd brać cele do komentowania" jest pojęciem Substacka |
| eksport subskrybentów | `/api/v1/subscriber/csv` | |
| rekomendacje publikacji | `/api/v1/recommendations/from/…` | |

**Najdroższe jest potwierdzanie, nie publikowanie.** Siedem funkcji istnieje
dlatego, że kliknięcie „opublikuj" nie znaczy, że coś wyszło. Kod ma osobną
stałą na ten przypadek — `POWOD_HOST_NIE_POKAZUJE = "Substack nie potwierdzil,
ze wyszlo"` — i cały mechanizm rozróżniania „nie wyszło" od „nie wiem".
Ta logika jest wynikiem pomiarów na żywym koncie (komentarz pod postem przepadał
w 7% prób, pod notką w 30%) i **każda nowa platforma wymaga zmierzenia jej od
nowa**. To nie jest praca programistyczna, tylko obserwacyjna, i trwa tygodniami.

**Wycena.** Osobny moduł platformy dla drugiej platformy to
**2000–2500 wierszy kodu** plus **kilka tygodni obserwacji na żywym koncie**.
Nie ma tu skrótu i nie warto go wygładzać.

## 4.3. Angielski

Nie da się przestawić polem, bo założenie siedzi w czterech różnych warstwach:

* **21 promptów napisanych po angielsku.** Model rozumie polecenie po angielsku
  i pisze po polsku, ale połowa reguł w tych promptach to przykłady i wzorce
  frazowe — te po tłumaczeniu przestają cokolwiek znaczyć.
* **Bramki `gates.py` to wyrażenia regularne po angielsku.** `ZAKAZANE_OTWARCIA`
  łapie `turn over`, `next time you`, `most people think`. `ZASTRZEZENIE` łapie
  `I think`, `in my view`. `NIBY_ZRODLO` łapie `in one survey`, `reportedly`.
  Po polsku **nie łapią nic** i przechodzą na zielono — czyli bramka znika po
  cichu, zamiast zgłosić, że nie działa. To jest dokładnie ten rodzaj awarii,
  przed którym ostrzega `DOKTRYNA.md` §12.
* **Korpus stylu jest po angielsku** i uczy rytmu angielskiego zdania.
* **`locale="en-US"`** w kontekście przeglądarki — interfejs Substacka po
  angielsku, żeby selektory tekstowe trafiały.

Dodatkowo bot **czyta pole `language` z API Substacka** i milczy pod postami
w obcym języku (`browser.py:2275, 2339, 2403`; etykieta `wrong_language`).
Powód jest zapisany: Substack tłumaczy cudze treści na język interfejsu
i podmienia je w HTML-u, więc treść bierze się wyłącznie z API.

**Wycena.** Druga wersja językowa to przepisanie 21 promptów (nie tłumaczenie —
przepisanie, bo przykłady muszą być z docelowego języka), przepisanie ~12
wyrażeń regularnych w `gates.py` i zebranie nowego korpusu stylu.
**Tydzień do dwóch, głównie pracy redakcyjnej, nie programistycznej.**

## 4.4. Temat AI

To jest najłatwiejsza z trzech rzeczy i jedyna, którą naprawdę zmierzyłem.
Zmiana tematu wymaga:

1. `HASLA_SZUKANIA` — ≥19 haseł w trzech obszarach (wymóg testu) — **KONFIG**;
2. `DZIEDZINY_CIEKAWOSTEK` — ≥29 opisów przy 14 wzorcach (wymóg testu) —
   **TEKST, kilka godzin**;
3. `korpus_kanalow.KANALY` — źródła tematów — **KONFIG**;
4. `OPRAWA` i `NIE_TEMAT` — odsiew nagłówków pod nową niszę — **TEKST**;
5. ~30 zdań w 14 promptach — **TEKST**;
6. 4 komunikaty systemowe w `stages.py` — **KOD, ale trywialny**;
7. 2 z 14 wzorców w `GENERATORY` (`SEEMING`, `UNBIDDEN` są o systemach AI) —
   **TEKST**;
8. przebudowa dokumentacji: `python agent-v2/dokumentacja-zrodla/sklej.py`;
9. poprawienie dwóch testów, które temat mają wpisany w ciało.

**Dzień pracy, w większości pisania, nie programowania.**

## 4.5. Rzeczy przywiązane do TEJ instalacji, o których łatwo zapomnieć

| co | gdzie | uwaga |
|---|---|---|
| ścieżka na serwerze | `systemd/*.service` — `/home/ubuntu/nia-substack-bot` | wpisana w trzech jednostkach |
| użytkownik `ubuntu` | jw. | |
| godziny przebiegów w UTC | `systemd/nia-agent.timer` | dobrane pod strefę czytelników, z zapisanym uzasadnieniem i sporem źródeł |
| `LIMIT_CZASU_PRZEBIEGU_S = 9000` **musi równać się** `TimeoutStartSec=9000` | `config.py` i `nia-agent.service` | jedna liczba w dwóch plikach; rozjazd znaczy, że agent liczy inny koniec niż systemd |
| **profile stylu leżą POZA `agent-v2/`** | `config.py:47` → `<korzeń repo>/style-profiles/` | `agent-v2/` nie jest samowystarczalny; bez tych plików etap `write` rzuca `StyleError` po opłaconym researchu |
| znacznik kopii testowej | plik `TO_JEST_KOPIA_TESTOWA` obok `config.py` | odbiera prawo do `--wyslij`; **dobry wzorzec, zostawić w produkcie** |
| baza rozdziela się sama | `DATA_DIR` wywodzi się z położenia `config.py` | osobny klon = osobna baza, bez zmiennej do zapomnienia |

## 4.6. Czego produkt NIE odziedziczy za darmo

Rzeczy, które w tym bocie działają, bo ktoś je zmierzył na żywym koncie —
i które u kogoś innego trzeba zmierzyć od nowa:

* odstępy między działaniami (5–15 min między komentarzami wynika z pomiaru:
  awaryjność potraja się po pierwszej akcji przy odstępie czterech minut);
* godziny publikacji (dwa źródła sprzeczne, decyzja „nie ruszamy" zapisana
  w timerze);
* dobór modeli per rola (A/B na tym samym materiale, w tym dwie próby ślepe);
* progi bramek (`SLOW_NA_BEAT = 150`, `BUDZET_ZASTRZEZEN = 1`);
* to, co doktryna nazywa wprost: **nie wiadomo, który kanał przynosi
  subskrypcje**. Zdanie „subskrypcje przynoszą artykuły" stało w dokumentacji
  do 2 września 2026 i **zostało obalone pomiarem**.

Konfigurator może te wartości wystawić jako pola. Nie może dać wraz z nimi
pewności, że są dobre dla cudzej niszy.

---

# CZĘŚĆ 5 — PROJEKT KONFIGURATORA

## 5.1. Kształt

Jeden plik `konfiguracja.toml` obok `agent-v2/`, czytany raz przy starcie
`config.py`. TOML, nie YAML — bo ma typy, komentarze i nie ma wcięć znaczących.

Zasada naczelna: **plik nie zastępuje `config.py`, tylko go zasila.** `config.py`
zostaje jedynym źródłem prawdy, przelicza sufity, waliduje i rzuca głośno przy
brakach. Konfiguracja podaje wartości, a nie decyzje.

Druga zasada: **każde pole ma sensowną wartość domyślną poza tożsamością
i kluczami.** Bez tego nowy operator ma do wypełnienia sto pól, zanim zobaczy
cokolwiek.

```toml
[konto]
platforma        = "substack"        # dziś jedyna wartość; patrz 5.4
uchwyt           = "nazwakonta"      # -> config.SUBSTACK_HANDLE + browser.PROFIL_HANDLE
nazwa_marki      = "Nazwa Pisma"     # -> prompty, profile stylu, WRITER_SYSTEM
strefa_czytelnika = "America/New_York"
ujawnia_ze_ai    = false             # -> WYLACZ_WYKRYWANIE_AI + prompts/OSWIADCZENIE_AUTORSTWA.md

[temat]
nisza_jednym_zdaniem = "this subject: what these systems do, how they are built, and who decides what they are allowed to do"
jezyk                = "English"     # -> ARTICLE_LANGUAGE, locale przeglądarki, SCOUT_SYSTEM
dziedziny            = [...]         # >= 29 pozycji (wymóg testu)
hasla_szukania       = [...]         # >= 19 pozycji w >= 3 obszarach (wymóg testu)

[zrodla]
kanaly_youtube = { "Nazwa" = "UC..." }
odsiew_naglowkow = [...]             # -> korpus_kanalow.OPRAWA
nie_temat        = [...]             # -> korpus_kanalow.NIE_TEMAT
blokowane_hosty  = [...]             # -> config.BLOCKED_HOSTS

[modele]
# jeden wiersz na rolę; klucz mówi, u kogo płacimy
write   = { model = "claude-fable-5-1", dostawca = "anthropic" }
note    = { model = "claude-opus-5",    dostawca = "anthropic" }
comment = { model = "deepseek-v4-pro",  dostawca = "deepseek" }
# ... 26 pozycji, z domyślnymi jak dziś

[modele.dostawcy]
anthropic = { klucz_z = "ANTHROPIC_API_KEY" }
deepseek  = { klucz_z = "DEEPSEEK_API_KEY", base_url = "https://api.deepseek.com" }
openai    = { klucz_z = "OPENAI_API_KEY", opcjonalny = true }

[wolumeny]
notki_dziennie      = 5
komentarze_dziennie = [15, 23]
lajki_dziennie      = [10, 16]
restacki_dziennie   = [1, 2]
follow_miesiecznie  = [10, 16]
subskrypcje_miesiecznie = [12, 20]
przebiegow_dziennie = 5
godziny_utc         = ["11:20", "17:00", "19:20", "21:30", "23:40"]

[pieniadze]
sufit_miesieczny_usd = 40.0
sufit_dzienny_usd    = 5.0
sufit_przebiegu_usd  = 1.60

[publikowanie]
okno_et            = [6, 22]
martwe_godziny_et  = [12, 13]
notek_promujacych  = 3
okno_promocji_dni  = 7
artykul_co         = "wtorek 14:00 UTC"
ciche_dni_na_ile   = 8

[styl]
korpus            = "prompts/styl/article_style_samples_v1.txt"
korpus_sha256     = "d4e4e..."
profile_katalog   = "style-profiles"
przypiete_akapity = [["OPENING", 65, "974f069d90"], ...]
zakazane_slowa    = [...]

[alarm]
email_do = ""                        # puste = alarmy wyłączone, cicho
```

## 5.2. Co trzeba przepiąć w kodzie, żeby ten plik naprawdę sterował

Rozdzielone tak, jak prosiło zlecenie: robota na dzień kontra przepisanie
modułu.

### Robota na jeden dzień — sześć zmian, każda mała

| # | co | gdzie | dlaczego to jest małe |
|---|---|---|---|
| 1 | wczytanie TOML-a na górze `config.py` i nadpisanie stałych | `config.py:1-60` | wszystkie stałe są już w jednym pliku; dochodzi ~40 linii wczytywania i walidacji |
| 2 | **usunięcie `browser.PROFIL_HANDLE`** i podmiana 11 użyć na `config.SUBSTACK_HANDLE` | `browser.py:789` + 11 miejsc | zamiana identyfikatora, zero logiki |
| 3 | dwa adresy panelu z uchwytu zamiast na sztywno | `browser.py:751-752` | dwie linie |
| 4 | 4 komunikaty systemowe z tematu zamiast na sztywno | `stages.py:113, 1181, 6847, 7196` | `SCOUT_SYSTEM = ("You are a topic scout for the %s-language %s '%s', a publication about %s...")` |
| 5 | kontrola kluczy po **dostawcy**, nie po identyfikatorze modelu | `llm.py:74-79` | naprawia dziurę z 3.1 przy okazji |
| 6 | przepisanie `.env.example` | `.env.example` | dziś opisuje poprzedniego agenta |

### Robota na kilka dni — cztery zmiany większe

| # | co | dlaczego to nie jest jednodniowe |
|---|---|---|
| 7 | **wyjęcie tematu z 14 promptów do pola** `{nisza}` | `stages._prompt` już podstawia pola, więc mechanizm jest. Ale zdania w promptach nie są jednym akapitem — temat wraca w przykładach, przeciwwskazaniach i kontrprzykładach (`skaut.md` ma 7 miejsc, w tym całą sekcję „Too vague"). Wymaga redakcji, nie zamiany. **Uwaga: jest test parzystości pól między kodem a promptem — `tests/test_generatory.py` — więc kod i prompt trzeba zmieniać razem** |
| 8 | **odwiązanie testów od tematu i konta** | `test_szukanie_celow` egzekwuje „każde hasło o AI", `test_kto_nas_czyta` ma wpisany uchwyt, `test_generatory` ma próg 400 komórek. Te asercje są **słuszne co do zasady** (pilnują, żeby rewir był szeroki i spójny z niszą) — trzeba je sparametryzować konfiguracją, a nie skasować |
| 9 | **korpus stylu jako profil, nie jako beton** | dziś: jeden plik, jeden SHA-256, pięć akapitów przypiętych po numerze i skrócie. Trzeba: katalog profili stylu, każdy z własnym manifestem, wybierany polem. Zabezpieczenie „nikt nie podmieni głosu po cichu" ma zostać — ale ma dotyczyć **wybranego profilu**, nie jednego pliku |
| 10 | **tryb pierwszej instalacji dla testów** | dziś świeży klon daje 6 czerwonych testów i nie da się odróżnić „brak playwrighta" od „kod zepsuty". Potrzebny znacznik „to jest świeża instalacja", który te sześć pomija z komunikatem, oraz `python -m agent_v2 sprawdz`, które mówi wprost, czego brakuje |

### Przepisanie modułu — dwie rzeczy

| # | co | wycena |
|---|---|---|
| 11 | **warstwa platformy** — wyjęcie `browser.py` + `kanal.py` za interfejs (`opublikuj_notke`, `opublikuj_artykul`, `skomentuj`, `odpowiedz`, `polub`, `podaj_dalej`, `obserwuj`, `subskrybuj`, `zasieg`, `czytelnicy`) i napisanie drugiej implementacji | ~2500 wierszy kodu + tygodnie obserwacji na żywym koncie. Patrz 4.2 |
| 12 | **druga wersja językowa** — 21 promptów, ~12 wyrażeń regularnych w `gates.py`, nowy korpus stylu | tydzień do dwóch pracy redakcyjnej. Patrz 4.3 |

## 5.3. Czego w konfiguratorze świadomie NIE wystawiać

Trzy rzeczy, które wyglądają na pola, a są decyzjami:

* **Sufit miesięczny jako pole „nieograniczony".** `MONTHLY_LIMIT_USD` to
  jedyna twarda blokada w systemie. `AGENT_V2_NO_LIMIT` już istnieje i już jest
  furtką — wystawienie jej w pliku konfiguracji zamienia ją w domyślną decyzję.
* **`WYLACZ_WYKRYWANIE_AI` bez kontekstu.** W `config.py:85-91` stoi wprost, że
  to „wybór publiczny, nie ustawienie techniczne", i że należał do właściciela,
  a nie do kodu. W konfiguratorze musi mieć ostrzeżenie, nie sam przełącznik.
* **Progi bramek jako liczby do pokręcenia.** `SLOW_NA_BEAT = 150`,
  `BUDZET_ZASTRZEZEN = 1`, `MIN_ZRODEL_DO_PISANIA = 4` — to wyniki pomiarów
  na konkretnych tekstach. Wystawione jako suwaki zostaną pokręcone w stronę
  „mniej blokuje", bo tak zawsze idzie.

## 5.4. Uczciwa odpowiedź na pytanie ze zlecenia

**Czy z tego da się zrobić konfigurowalny produkt?**

Tak — jeśli produktem jest **„anonimowe pismo na Substacku, po angielsku,
o dowolnym temacie"**. To jest dzień pracy na przepięcie plus dzień na
przepisanie tekstów pod nową niszę. Fundament jest do tego gotowy: stałe są
w jednym pliku, prompty czytane z dysku przy każdym wywołaniu, baza rozdziela
się sama, znacznik kopii testowej istnieje, a księgowanie kosztu jest wpięte
w każde płatne wywołanie i pilnowane testem.

Nie — jeśli produktem ma być **„bot na dowolną platformę"**. To jest napisanie
drugiego `browser.py` od zera i kilka tygodni mierzenia, czego nowa platforma
nie potwierdza. Ta praca nie skraca się przez lepszą architekturę, bo jej
większość nie jest programowaniem.

Pośrodku stoi język, i to jest część najczęściej niedoceniana: bramki
`gates.py` po zmianie języka **nie krzyczą, tylko cicho przestają cokolwiek
łapać**. Produkt, który pozwoli wybrać język bez wymiany bramek, będzie
publikował teksty bez żadnej kontroli formy — i nikt się nie dowie, bo wszystko
świeci na zielono.
