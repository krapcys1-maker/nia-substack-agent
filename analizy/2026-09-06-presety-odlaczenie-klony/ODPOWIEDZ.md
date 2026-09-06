# Odpowiedź na audyt odłączania: co potwierdzone, co naprawione, co zostaje

Data: 6 września 2026. Gałąź `presety`. Punkt wyjścia: commit `adcac83` (badany
przez audyt w `RAPORT.md` obok). Weryfikacja i naprawa w tym samym repozytorium,
bez publikowania i bez płatnych wywołań.

## 1. Odpowiedź na pytanie „czy po odłączeniu mamy świeżego bota"

Na commicie `adcac83`: **nie w pełni**. Sześć z trzynastu ustaleń audytu
(F01–F06) potwierdziłem w kodzie, każde na konkretnej funkcji:

| Ustalenie | Miejsce w kodzie przed naprawą | Potwierdzone |
|---|---|---|
| F01 odłączenie nie unieważnia procesu | `preset.wymagaj_aktywnego` pytało tylko obiekt `cfg.PRESET_AKTYWACJA` w pamięci; `odlacz` usuwał plik | tak |
| F02 `AGENT_V2_PRESET` omija „odłączono" | `preset.aktywacja` daje zmiennej pierwszeństwo, źródło `srodowisko`, brama przepuszczała ją w produkcji | tak |
| F03 instancja bez właściciela | `preset.podlacz` brało `instancja or preset.nazwa`, katalog bez manifestu | tak |
| F04 stary `konfiguracja.toml` wraca | gałąź `else` w `config.py` czytała plik zawsze, gdy nie było aktywacji | tak |
| F05 pusty korpus = korpus silnika; zapas w repo | `konfiguracja.zastosuj`: puste pole zostawiało domyślną ścieżkę silnika; `preset._rozwiaz_sciezki` szukało pliku w repo, gdy nie było go w paczce | tak |
| F06 odcisk bez treści stylu, zależny od miejsca | `preset.odcisk` liczył pola (ścieżki bezwzględne po `_rozwiaz_sciezki`) i bloki | tak |

Po naprawie (ten commit) odpowiedź brzmi: **tak, w zakresie silnika i pamięci
redakcyjnej**. Granice konta, przeglądarki, wspólnego rachunku i nazw usług
(F08–F10) oraz eksport paczki, cache zadań i przełączanie w pamięci (F07,
F12, F13) zostają otwarte, zgodnie z sekcją 8 raportu.

## 2. Co zmieniono w silniku

Wszystko to silnik (bot czysty), nie kartridż. Kartridże `ai` i lokalny `nia`
nie wymagały zmian; `nia` trzeba było tylko podłączyć ponownie, bo zmienił
się sposób liczenia odcisku.

1. **Generacja aktywacji** (`preset.aktywacja_nadal_wazna`). Przed każdym
   płatnym wywołaniem (`llm._preflight`) i przed każdym zapisem na koncie
   (`browser.naprawde_wyslac`) proces czyta wskaźnik i porównuje odcisk oraz
   instancję ze swoją aktywacją. Po `odlacz` albo po `podlacz` innego presetu
   stary proces dostaje odmowę z powodem. Brama startu też to sprawdza.
2. **Podgląd ze środowiska** (`preset.tylko_podglad`). Aktywacja
   z `AGENT_V2_PRESET` nadal powstaje (podgląd promptów, testy), ale nie ma
   prawa do płatnych wywołań ani publikacji. `status` ostrzega, gdy zmienna
   jest w środowisku.
3. **Właściciel instancji** (`wlasciciel.json`, `preset._sprawdz_wlasciciela`).
   Pierwsze `podlacz` zapisuje preset i uchwyt konta. Inny preset albo inne
   konto na tym samym `--instancja` dostaje odmowę i radę o nowej nazwie.
   `--przejmij` to jawna decyzja, zapisana w dzienniku instancji.
4. **Bez kartridża nie wraca stary temat.** Bez aktywacji `config.py` nie
   czyta `konfiguracja.toml`; wyjątkiem jest darmowy test (testy konfiguracji
   na nim stoją) i jawne `AGENT_V2_KONFIGURACJA_TOML=1`. Na ekranie jest
   komunikat z drogą migracji (`importuj-konfiguracje`).
5. **Pusty korpus = brak korpusu** (`preset._bez_domyslnego_korpusu`).
   Kartridż z pustym `styl.korpus` wskazuje własny `styl/korpus.txt`; gdy go
   nie ma, pisarz dostaje zero przykładów. Ścieżki względne w katalogu presetu
   rozwiązują się tylko tam; plik wspólny z repozytorium wybiera się jawnie
   przez `repo:style-profiles/...`.
6. **Odcisk paczki** (`preset.odcisk` z `zasoby`). Pola jak w TOML-u (ścieżki
   względne), bloki promptów i skróty SHA-256 plików stylu z katalogu presetu
   (profile, korpus, przypięcia). Kopia katalogu ma ten sam odcisk; zmieniony
   profil to inny odcisk i odmowa startu do czasu `podlacz`.

## 3. Dowody

- `agent-v2/tests/test_swiezy_bot_po_odlaczeniu.py`: 41 sprawdzeń, po jednej
  sekcji na próby P02/P17, P03/P19, P04, P10, P06/P07/P09, P18, każda
  z kontrdowodem. Bez sieci, bez płatnych wywołań.
- `agent-v2/tests/test_presety.py`: sekcja 10 zaktualizowana do nowej
  semantyki bramy (stary obiekt w pamięci po `odlacz` nie przechodzi).
- Sąsiednie testy przeglądarki, konfiguracji i bramek bez zmian wyniku.

## 4. Co zostaje otwarte i dlaczego nie teraz

| Ustalenie | Powód odłożenia |
|---|---|
| F07 eksport paczki | wymaga formatu archiwum i importu do katalogu tymczasowego; dziś przenosi się cały katalog presetu |
| F08 wspólny Chrome i port 9222 | zmiana profilu przeglądarki na klon dotyczy środowiska uruchomieniowego, nie tylko kodu |
| F09 wspólny rachunek między instancjami | potrzebna księga kosztów właściciela kluczy ponad bazami instancji |
| F10 nazwy jednostek systemd | parametryzacja nazw po identyfikatorze instancji w generatorze |
| F11 strategie redakcyjne | osobna warstwa promptów na gatunek, poza zakresem czystości |
| F12 cache zadań | klucz z hashem wejścia i wersją promptu |
| F13 `zastosuj` bez transakcji | dziś wymiana idzie przez nowy proces; `podlacz` waliduje kopię wcześniej |
