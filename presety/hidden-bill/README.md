# The Hidden Bill

**The terms that change what everyday life costs.**

Gotowy preset anglojęzycznej publikacji o kosztach i warunkach codziennych
zakupów: subskrypcjach, dopłatach, cenach zależnych od danych, naprawach
oraz dostępie do kupionych urządzeń i usług. Jego obietnica dla czytelnika:
po jednym tekście lepiej rozumiesz konkretny zakup i wiesz, jaki warunek
sprawdzić. Głos jest rzeczowy, uważny, czasem lekko ironiczny.

Nie jest to poradnik inwestycyjny ani codzienny przegląd afer. Publikacja
ma również wyjaśniać korzystne rozwiązania i przypadki, w których popularne
oskarżenie jest zbyt szerokie. Nazwa jest propozycją redakcyjną; nie
rezerwowano adresu publikacji ani nie sprawdzano praw do marki.

**Dlaczego ten temat**

Łączy znajomy problem z dokumentem, który potrafi zmienić jego rozumienie.
Sąsiednie obszary mają widoczną publiczność na Substacku: w odczytanym
6 września 2026 zestawieniu Business znajdują się m.in. BIG, Feed Me
i publikacje o ekonomii codzienności. To sygnał popytu, nie pomiar CTR
nowej redakcji. Uzasadnienie, alternatywy i źródła: [RESEARCH.md](RESEARCH.md).

**Co rzeczywiście podłącza się do bota**

| Element | Zawartość |
|---|---|
| [preset.toml](preset.toml) | Temat, konto przykładowe, modele, harmonogram, źródła, budżety, ścieżki stylu |
| `prompty/` | Wszystkie 7 obsługiwanych bloków; wskazówki dla scouta, banku i poszczególnych form |
| `styl/` | Własny profil pozytywny i negatywny, 10 oryginalnych akapitów, 5 przypiętych przykładów |
| [START.md](START.md) | 12 pomysłów na teksty, dokumenty wejściowe, warunki weryfikacji, plan pierwszych tygodni |
| [PROBKI.md](PROBKI.md) | Przykłady głosu i konstrukcji tytułów do oceny przez operatora |
| [PROBKI_PELNE.md](PROBKI_PELNE.md) | Pełne teksty, Notki, komentarze i poprawki na jawnie fikcyjnych przykładach |
| [OCENA_JAKOSCI.md](OCENA_JAKOSCI.md) | Kryteria odbioru tekstów i pomiar jakości oraz kosztów |
| [WERYFIKACJA.md](WERYFIKACJA.md) | Wyniki sprawdzenia paczki i jego ograniczenia |

Pliki README, RESEARCH, START, PROBKI, PROBKI_PELNE i OCENA_JAKOSCI są dokumentacją
operatora. **Obecny silnik nie importuje automatycznie START.md do banku.**
Zasady konieczne do bieżącego działania znajdują się też w TOML-u i
ładowanych blokach promptów. Nie dopisano nieobsługiwanych pól ani
fikcyjnego mechanizmu startowej kolejki.

**Ustawienia startowe**

| Parametr | Ustawienie |
|---|---|
| Język i odbiorca | English; przede wszystkim USA, z jawnym oznaczaniem przykładów UK/EU |
| Notki | 2 sloty dziennie, z cichym dniem według konfiguracji silnika |
| Artykuł | 1 tygodniowo, czwartek 14:00 UTC |
| Przebiegi dzienne | 13:30 i 20:30 UTC |
| Komentarze / polubienia | 2–3 / 3–5 dziennie; tylko przy sensownych okazjach |
| Restacki | 0–1 dziennie |
| Obserwacje i subskrypcje | Wyłączone |
| Źródła sygnałów | 6 sprawdzonych RSS/Atom; bez zależności od YouTube |
| Modele | 25 jawnie określonych ról tekstowych; nazwy obsługiwane przez obecny kod |
| Okładki | Wyłączone na start; kompletny blok wizualny czeka na ich włączenie |
| Limity | 25 USD/miesiąc, 3,50 USD/dzień, 1,60 USD/przebieg |

Godziny są ustawieniem początkowym do pomiaru, nie odkrytym „najlepszym
czasem publikacji”. Ze względu na stałe UTC lokalna godzina zmienia się
wraz z czasem letnim/zimowym. Liczby treści oznaczają plan i limity,
nie obietnicę realizacji przy dowolnym koszcie i dostępności materiału.

Pisarz artykułu korzysta z `claude-fable-5-1`, główne notki i naprawa
z `claude-opus-5`; selekcja, research i pozostałe role z odpowiednio
przypisanych `deepseek-v4-flash` lub `deepseek-v4-pro`. Weryfikację faktów
przypisano do Pro. To konfiguracja oparta na dostępnych ścieżkach
projektu, bez nowego adaptera i bez płatnego benchmarku modeli.

Miesięczny limit jest ograniczeniem, nie prognozą wydatków. Obecny
mechanizm kosztów nie stanowi wspólnego licznika wszystkich instancji
korzystających z tych samych kluczy. Sufity tokenów i poziomy wysiłku
pozostają parametrami silnika. Nie udajemy, że preset potrafi je nadpisać.

**Sprawdzenie bez aktywacji**

Uruchamiane z katalogu głównego repozytorium:

```powershell
python -B narzedzia/presety.py sprawdz hidden-bill
python -B narzedzia/presety.py pokaz hidden-bill
python -B narzedzia/presety.py podglad hidden-bill
```

W repo pozostaje publiczny przykład `konto.uchwyt = "your-handle"`.
Ta wartość jest zgodna z konwencją presetu AI. Nowsza walidacja
aktywacji odrzuca ją, jeśli nie dostanie rzeczywistego uchwytu przez
konfigurację instalacji. **Publiczna paczka nie zawiera Twojego konta.**

Skopiuj `.env.example` do `agent-v2/.env` w świeżej instalacji i wpisz
własne `SUBSTACK_HANDLE`, `NAZWA_MARKI` oraz klucze Anthropic i DeepSeek.
Pozostaw `DRY_RUN=true` podczas konfiguracji. **Publiczny preset zostaje
niezmieniony.** Wartości konta ze środowiska mają pierwszeństwo przed
TOML-em; nie przenoś bez sprawdzenia `.env` poprzedniej redakcji.

Prywatna kopia całego katalogu do `presety/hidden-bill-local/` jest
potrzebna dopiero do zmiany stylu, tematu, modeli lub wolumenów. W takiej
kopii ustaw `preset.nazwa = "hidden-bill-local"`; konto nadal trzymaj
w `.env`. Katalog prywatnej kopii jest ignorowany przez Git.

Sprawdź preset i podgląd. Jeżeli zastępuje obecną redakcję,
zatrzymaj jej harmonogram i pracujące procesy. Wybierz nową, nieużywaną
instancję i dopiero wtedy wykonaj polecenie aktywacji, np.:

```powershell
python -B narzedzia/presety.py podlacz hidden-bill --instancja hidden-bill-start
```

Po aktywacji zapisz sesję przeglądarki dla tej instancji zgodnie z
[instrukcją instalacji](../../docs/INSTALL.md). Potwierdź konto
przeglądarki, odrębność danych i właściwy harmonogram przed publikacją.
Przy równoległych klonach nadal potrzebne są rozdzielone profile/endpointy
Chrome oraz brak kolizji nazw usług. Sam katalog presetu tego nie ustawia.

**Przenoszenie i zmiany**

Przenoś pełny katalog `hidden-bill/`, a nie wynik eksportu samego TOML-a.
Paczka nie zawiera kluczy, cookies, baz, kolejki ani wskaźnika aktywacji.
Ścieżki w TOML-u są względne i wskazują wyłącznie jej własny styl.

Po zmianie korpusu w prywatnej kopii użyj istniejącego narzędzia:

```powershell
python -B narzedzia/przypnij_styl.py --korpus presety/hidden-bill-local/styl/korpus.txt --wybor OPENING=0,CONCRETE_TO_SYSTEM=1,MECHANISM=2,COUNTERARGUMENT=3,ENDING=4
```

Następnie ponownie sprawdź preset i podgląd. Korpus zawiera przykłady
stworzone do tej paczki, z jawnie ilustracyjnymi przypadkami; nie jest
zbiorem dowodów ani kopią głosu istniejącego autora.
