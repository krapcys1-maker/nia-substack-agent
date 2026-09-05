# Presety — jak podłączyć i odłączyć całą redakcję

Stan na 5 września 2026, gałąź `presety`. Ten dokument opisuje mechanizm
wprowadzony po audycie `analizy/2026-09-05-czystosc-presety/RAPORT.md`.
Angielskie streszczenie dla obcego operatora stoi w `presety/README.md`.

## Cztery rzeczy, których nie wolno mieszać

| Rzecz | Gdzie leży | Co zawiera |
|---|---|---|
| **Silnik** | `agent-v2/*.py`, `prompts/`, `style-profiles/` | etapy, bramki, adaptery, wartości domyślne. Nie zna konta. |
| **Preset** | `presety/<nazwa>.toml` (własne, poza gitem) i `presety/przyklady/` (w gicie) | nagłówek `[preset]` plus komplet pól: konto, temat, styl, źródła, modele, wolumeny, harmonogram, publikowanie, pieniądze |
| **Instancja** | `agent-v2/instancje/<nazwa>/` | baza SQLite, bank pomysłów, cache etapów, szkice, kolejka promocji, dziennik działań TEGO presetu |
| **Aktywacja** | `agent-v2/aktywny_preset.json` | który preset, z jakim odciskiem, w której instancji, który raz |

Sekrety (`agent-v2/.env`) i sesja Substacka pozostają poza presetem. Preset
da się wysłać komuś mailem; klucze nie.

## Polecenia

```bash
python narzedzia/presety.py lista                 # co jest, co podłączone (*)
python narzedzia/presety.py sprawdz ai            # błędy i uwagi, bez płatnych wywołań
python narzedzia/presety.py pokaz ai              # rozwiązane stałe: preset czy silnik
python narzedzia/presety.py podglad ai            # prompty tak, jak zobaczy je model
python narzedzia/presety.py podlacz ai            # aktywacja
python narzedzia/presety.py status
python narzedzia/presety.py odlacz
python narzedzia/presety.py importuj-konfiguracje --nazwa moje   # stary konfiguracja.toml -> preset
python narzedzia/presety.py eksportuj ai > kopia.toml            # znormalizowany TOML, bez sekretów
```

Po `podlacz` i `odlacz` **procesy uruchamia się od nowa**. Kontekst jest
czytany raz, przy starcie; działający przebieg dokończy pracę w starym
kontekście. Zegary systemd buduje się z presetu:
`python narzedzia/jednostki.py --katalog /srv/bot --uzytkownik bot`.

## Co się dzieje przy podłączeniu

1. Plik jest czytany i sprawdzany **w całości**: nieznane pole, zła wartość,
   niespójny zegar, brak pliku profilu stylu, model bez ścieżki dostawcy —
   każde z tych zatrzymuje `podlacz` **zanim** cokolwiek zostanie zapisane.
   Poprzedni preset zostaje podłączony bez zmian.
2. Powstaje katalog instancji (domyślnie `instancje/<nazwa>`; inna nazwa przez
   `--instancja` daje świeży katalog, ten sam preset).
3. Wskaźnik aktywacji jest zapisywany atomowo (plik tymczasowy i `os.replace`).
4. Przy każdym starcie `config.py` czyta wskaźnik, wczytuje preset z pliku,
   porównuje odcisk SHA-256 pól z odciskiem z aktywacji, **przywraca neutralną
   bazę silnika** i dopiero na nią nakłada pola presetu. Preset zmieniony po
   aktywacji zatrzymuje start z komunikatem, co zrobić.

Z tego wynika własność, o którą chodziło w audycie: preset B skompilowany po
używaniu A daje **ten sam kontekst** co B na czystym silniku. Pilnuje tego
`agent-v2/tests/test_presety.py`, sekcja 3.

## Co się dzieje przy odłączeniu

`odlacz` usuwa wskaźnik i dopisuje wpis do dziennika instancji. Dane instancji
zostają — ponowne `podlacz` tego samego presetu je wznawia. Bez wskaźnika:

- `run.py` i `artykul_z_puli.py` odmawiają startu (kod wyjścia 3, komunikat
  z poleceniami). Nie ma powrotu do „wbudowanego tematu": silnik go nie ma.
- `alarm.py` zgłasza kontrolę `preset` jako pierwszą — brak presetu jest
  alarmem, nie ciszą.
- Zegary systemd trzeba wyłączyć ręcznie (`odlacz` wypisuje polecenie).

Wyjątek: w **darmowym teście** (proces uruchomiony z `agent-v2/tests/`) brama
milczy, tak samo jak zapora płatnych wywołań. Testy pracują na silniku, nie na
tym, co operator akurat podłączył.

## Pola presetu

Kontrakt pól jest jeden — `konfiguracja.POLA` — wspólny dla presetu, starego
`konfiguracja.toml` i wsadów tematycznych. Nowe sekcje i pola z 5 września:

| Pole | Co robi |
|---|---|
| `wolumeny.notki_dziennie` | liczba slotów notek na dobę, jedna dla zwykłego dnia i dnia artykułu; promocja artykułu zajmuje slot, nie dokłada go; `0` wyłącza notki |
| `publikowanie.miks_notek` | proporcje typów, którymi sloty wypełniają się cyklicznie |
| `wolumeny.artykuly_tygodniowo` | `0` wyłącza ścieżkę artykułu (zegar, promocję, `artykul_z_puli`) |
| `harmonogram.dni_artykulu`, `harmonogram.godzina_artykulu_utc` | dni i godzina zegara artykułu; bez dni silnik dobiera je z liczby |
| `harmonogram.godziny_przebiegow_utc` | zegar rutyny dnia; liczba godzin musi zgadzać się z `przebiegow_dziennie` |
| `styl.opis` | głos opisany słowami, wstrzykiwany do briefów pisarza, notki, komentarza i odpowiedzi jako `{styl_opis}` |
| `styl.profil_pozytywny`, `styl.profil_negatywny` | ścieżki profili stylu względem korzenia repozytorium |
| `styl.korpus`, `styl.wymagaj_korpusu` | plik korpusu i czy pisarz ma odmówić bez przypiętego korpusu |
| `modele.obraz` | model okładki; pusty napis wyłącza okładkę; ustawia naraz rolę i model żądania |
| `modele.zapasowy_pisarz` | na jaki model wraca pisarz po awarii; pusty = zatrzymaj się |

Walidatory sprawdzają dziedzinę wartości, nie tylko typ: liczności są
nieujemnymi liczbami całkowitymi, kwoty skończone i nieujemne, strefa musi
istnieć w bazie IANA, data być dniem w kalendarzu, godziny mieścić się w dobie.

Role modeli podane w presecie nakładają się na **domyślne silnika**, nigdy na
poprzedni preset. `pokaz` wypisuje przy każdej roli, skąd pochodzi.

## Co jest izolowane, a co celowo wspólne

| Izolowane per instancja | Wspólne |
|---|---|
| baza, bank pomysłów, indeks kandydatów, zużyte fakty, przegrane tematy | klucze API (`agent-v2/.env`) |
| cache etapów (`cache/<etap>.<odcisk>.json`) | sesja przeglądarki i profil Chrome |
| stan dziedziny (`aktualne_modele.json`, pamięta pytanie) | kod, prompty, profile stylu w repozytorium |
| oczekujący artykuł i kolejka promocji (znacznik `instancja`) | |
| dziennik działań, czytelnicy, obserwowani — w katalogu instancji | |

Dziennik działań w katalogu instancji oznacza, że nowa instancja **nie pamięta
komentarzy poprzedniej** i może wrócić pod ten sam post. To znane ograniczenie
tej wersji; wznowienie tej samej instancji (`podlacz` tej samej nazwy) pamięta.

## Przykład: preset „ai"

`presety/przyklady/ai.toml` — AI po angielsku, dwie notki dziennie, jeden
artykuł we wtorek, trzy przebiegi dziennie, komentarze 3–5, polubienia 5–8,
restacki, obserwacje i subskrypcje wyłączone, pisarz na `claude-fable-5-1`,
notki na `claude-opus-5`, opis głosu w `styl.opis`, korpus opcjonalny.
Skopiuj do `presety/moj-ai.toml`, zmień `[preset].nazwa` i `[konto]`, uruchom
`sprawdz`, potem `podlacz`.

## Co ten mechanizm jeszcze nie robi

- Nie wymienia kontekstu w pracującym procesie — po przełączeniu trzeba
  uruchomić procesy od nowa.
- Nie waliduje kluczy u dostawców — mówi tylko, których brakuje w środowisku.
- Nie ma osobnych profili stylu dla notki i komentarza — jest jeden `styl.opis`
  wspólny dla form krótkich i długiej.
- Nie rozdziela źródeł na role (sygnał, dowód, miejsce rozmowy) — są kanały
  YouTube i lista blokowanych hostów, jak dotąd.
- `konfiguracja.toml` jest nadal czytany, gdy presetu nie ma — na czas
  przejścia; przy podłączonym presecie jest ignorowany z komunikatem.
