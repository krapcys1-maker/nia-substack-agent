# Presety, instancje i granice izolacji

Stan opisany dla wersji z 6 września 2026. Instrukcja dla nowego użytkownika:
[INSTALL.md](INSTALL.md). Wnioski o gotowości produktu:
[raport dystrybucji](../analizy/2026-09-06-dystrybucja-github/RAPORT.md).

## Trzy oddzielne warstwy

**Silnik** zawiera przebieg researchu i pisania, kontrakty etapów, wspólne
prompty, reguły form, kontrolę kosztów i przeglądarkę. Nie ma domyślnego
aktywnego tematu. Nadal ma własne założenia redakcyjne i techniczne; „neutralny
tematycznie” nie oznacza dowolnego stylu, języka lub dostawcy modeli.

**Preset** jest paczką tematu i ustawień. Publiczne paczki `ai` oraz
`hidden-bill` zawierają placeholder konta; rzeczywiste konto i klucze pochodzą
z lokalnego `agent-v2/.env`. Wybranie publicznej paczki nie wymaga jej edycji.

**Instancja** przechowuje bank pomysłów, szkice, cache, koszty, dzienniki i zapis
sesji. Jest osobnym katalogiem `agent-v2/instancje/<id>/`. Jeden checkout ma
jeden wskaźnik `agent-v2/aktywny_preset.json` i jeden aktywny kontekst naraz.

| Plik lub katalog | Funkcja |
|---|---|
| `presety/<nazwa>/preset.toml` | Temat, źródła, wolumeny, harmonogram, modele, budżety, styl |
| `presety/<nazwa>/prompty/` | Siedem obsługiwanych bloków redakcyjnych |
| `presety/<nazwa>/styl/` | Profile pozytywny/negatywny, opcjonalny korpus i przypięcia |
| `agent-v2/.env` | Konto, API, ustawienia środowiska instalacji |
| `agent-v2/aktywny_preset.json` | Lokalny wybór paczki, odcisk i instancja |
| `agent-v2/instancje/<id>/wlasciciel.json` | Zapis właściciela danych: preset i uchwyt |
| `agent-v2/instancje/<id>/storage-state.json` | Lokalny zapis sesji Substacka |

## Polecenia operatora

```bash
python narzedzia/presety.py lista
python narzedzia/presety.py sprawdz ai
python narzedzia/presety.py pokaz ai
python narzedzia/presety.py podglad ai
python narzedzia/presety.py podlacz ai --instancja moja-redakcja
python narzedzia/presety.py status
python narzedzia/presety.py odlacz
```

`sprawdz` oraz `podglad` nie wywołują modeli. Walidacja nie jest próbą dostępu
do API ani testem jakości tekstu. `podglad` składa briefy z blokami i przykładami;
pełne profile stylu trzeba też przeczytać w ich plikach.

`podlacz` najpierw sprawdza paczkę, a potem atomowo zapisuje wskaźnik.
Błędna nowa paczka nie zastępuje dotychczasowej. Konto z `.env` nadpisuje
konto przykładowe; nierozwiązany placeholder blokuje aktywację. Brak klucza
może zostać ostrzeżeniem, a odmowa nastąpi przed wymagającym go wywołaniem.

Po aktywacji uruchamiaj nowe procesy i zapisuj sesję do nowej instancji.
Nie edytuj promptów pod działającym przebiegiem.

## Co daje odłączenie

`odlacz` usuwa wskaźnik i zapisuje zdarzenie w historii instancji. Nowy
standardowy przebieg bez presetu odmawia pracy. Stary proces sprawdza przed
kolejnym wywołaniem modelu lub zapisem na koncie, czy jego aktywacja nadal
pasuje do wskaźnika.

To nie jest pełne wyczyszczenie instalacji. Pozostają:

- dane poprzedniej instancji i jej sesja;
- klucze oraz konto w `.env` i eksportowanych zmiennych;
- otwarty Chrome i jego profil;
- zainstalowane zadania systemu i pracujące procesy;
- opublikowane treści i historia po stronie Substacka.

Odłączenie nie cofa żądania już wysłanego do zewnętrznego serwisu. Obecna
kontrola ważności porównuje odcisk i ID instancji, ale nie numer aktywacji:
szybkie odłączenie i ponowne podłączenie tej samej paczki do tego samego ID
może ponownie dopuścić stary proces. **Zatrzymanie procesów pozostaje częścią
procedury przełączenia.**

Stary `agent-v2/konfiguracja.toml` nie wraca automatycznie po odłączeniu.
Odczyt pozostaje dostępny w testach lub przez jawne
`AGENT_V2_KONFIGURACJA_TOML=1` dla migracji/diagnostyki.
`AGENT_V2_PRESET=<plik>` jest podglądem; produkcja wymaga wskaźnika.

## Nowy temat i stare dane

Dla nowego tematu wybierz nowe ID instancji. Ponowne użycie starego ID oznacza
wznowienie danych. Podłączenie innego presetu lub konta do zajętego ID jest
odrzucane przez kontrolę właściciela; `--przejmij` świadomie przejmuje katalog,
ale nie usuwa jego zawartości.

Właściciel jest sprawdzany przy podłączaniu. Nie zastępuje to sprawdzenia
rzeczywistego zalogowanego użytkownika przeglądarki. Zmiana konta w `.env`
wymaga ponownej aktywacji, właściwego nowego ID oraz potwierdzenia sesji.

Nowa lokalna instancja nie usuwa historii z tego samego konta Substack.
Odczyt konta może ponownie przynieść wcześniejsze treści. Osobne publikacje
najlepiej uruchamiać w świeżych klonach z właściwymi kontami.

## Przenośność stylu i paczki

Względne ścieżki zasobów katalogowego presetu rozwiązują się wewnątrz paczki.
Wspólny zasób z repo wybiera się jawnie prefiksem `repo:`.
Odcisk obejmuje pola, ładowane bloki promptów i treść wskazanych plików stylu;
przeniesienie kompletnej paczki zachowuje odcisk, a zmiana profilu go zmienia.

Puste `styl.korpus` nie sięga do starego korpusu silnika. Dla paczki katalogowej
loader ustawia jednak jej własny `styl/korpus.txt`: jeśli taki plik istnieje,
może zostać wczytany. Aby mieć zero przykładów, wyłącz wymóg korpusu i usuń
korpus z prywatnej paczki albo jawnie ustaw odpowiednią nieistniejącą ścieżkę.
Sam pusty napis nie oznacza „nigdy nie ładuj żadnego pliku”.

`eksportuj` zwraca sam TOML. Do innej instalacji przenoś cały katalog paczki;
nie dołączaj `.env`, wskaźnika, sesji ani danych instancji.

## Komputer i serwer

Lokalne uruchamianie jest dostępne przez CLI. Na Windows zadania harmonogramu
konfiguruje operator. Linux ma generator systemd
`narzedzia/jednostki.py`, który korzysta z harmonogramu aktywnego presetu.

Kilka klonów na jednym komputerze nie daje jeszcze pełnej izolacji:
Chrome używa portu 9222 i profilu pod katalogiem użytkownika, a usługi mają
stałe nazwy `nia-agent`, `nia-artykul`, `nia-alarm`. Osobne instancje rozdzielają
pliki sesji, ale połączenie do działającego Chrome może korzystać ze wspólnego
zalogowanego kontekstu. Serwer wymaga osobnego przygotowania Chrome, ekranu
i logowania; generator timerów tego nie robi.

## Co pozostaje pracą rozwojową

- Jeden kreator instalacji i diagnostyka przed płatnym przebiegiem.
- Uwierzytelniona kontrola konta, konfiguracja portu/profilu Chrome per instalacja.
- Osobne nazwy usług i generator Windows, usuwanie nieaktualnych zadań.
- Numer generacji aktywacji sprawdzany przez wszystkie działające procesy.
- Wspólny licznik kosztów dla kluczy używanych w kilku instancjach.
- Pełny eksport paczki i jawny import początkowych pomysłów.
- Więcej założeń stylu, języka i generowania wystawionych w schemacie presetu.
- Test całej ścieżki na świeżym Windows i Linux oraz powtarzalne wydania.

Szczegóły, priorytety i kryteria odbioru:
[raport dystrybucji](../analizy/2026-09-06-dystrybucja-github/RAPORT.md).
