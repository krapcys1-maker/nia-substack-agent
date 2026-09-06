# Sprawdzenie paczki The Hidden Bill

Data: 6 września 2026. Preset: `hidden-bill`, schema 1, wersja `2026-09-06`.

**Wynik: paczka przechodzi obecny loader, podgląd i próby izolacji.**
Nie była aktywowana w używanej instalacji. Nie wygenerowano płatnego
tekstu, nie opublikowano treści i nie zmieniono sesji ani kluczy.

Testy wykonano poza repozytorium, w kopii aktualnych plików roboczych
gałęzi `presety`, uwzględniającej istniejące poprawki silnika. Nie
testowano wyłącznie dawnego commita z poprzedniego audytu. Kopia nie
zawierała lokalnego `.env` ani aktywnego wskaźnika użytkownika;
wywołania modeli i przeglądarki nie były potrzebne.

**Sprawdzenia konsoli**

| Polecenie / próba | Wynik |
|---|---|
| `presety.py sprawdz hidden-bill` | Kod 0, 0 błędów |
| `presety.py podglad hidden-bill` | Kod 0; złożone prompty, 5 przykładów stylu |
| Istniejący `agent-v2/tests/test_presety.py` | 162 sprawdzenia udane, 0 nieudanych |
| Dodatkowe sprawdzenia tej paczki | 24 udane, 0 nieudanych |
| 6 adresów feedów w TOML-u | HTTP 200, poprawny XML i wpisy przy odczycie |
| Odczyt tych feedów parserem bota | Wszystkie dają kandydatów |

Uwagi walidatora są oczekiwane: przykładowy uchwyt konta, brak kluczy
Anthropic/DeepSeek w odizolowanej kopii oraz celowo wyłączone
obserwacje i subskrypcje. Nowsza brama **odrzuciła aktywację publicznego
uchwytu**. Aktywacja z fikcyjną tożsamością przekazaną środowiskiem
przeszła wyłącznie w kopii testowej, po czym preset odłączono.

**Zakres 24 dodatkowych sprawdzeń**

1. Publiczny preset przechodzi walidację do oceny.
2. Zawiera dokładnie siedem obsługiwanych bloków.
3. Każdy blok różni się od odpowiadającego bloku presetu AI.
4. Nie zawiera niewypełnionych znaczników redakcyjnych `<<...>>`.
5. Wszystkie trzy ścieżki stylu prowadzą do tej paczki.
6. Każde hasło wyszukiwania zawiera znacznik niszy.
7. Paczka zawiera 30 haseł i 32 obszary poszukiwań.
8. Nałożenie po AI daje te same ustawienia objęte resetem co nałożenie na bazę.
9. Nie pozostają kanały RSS/YouTube presetu AI.
10. Wszystkie 25 ról tekstowych ma jawną konfigurację.
11. Generowanie obrazów jest wyłączone.
12. Ilości i harmonogram odpowiadają planowi 2 notek, 1 artykułu i 2 przebiegów.
13. Loader stylu wczytuje pięć poprawnie przypiętych fragmentów.
14. Ładowane są własne profile The Hidden Bill.
15. Każdy wybrany fragment pochodzi z korpusu tej paczki.
16. Przeniesienie kompletnego katalogu zachowuje odcisk presetu.
17. Po przeniesieniu wszystkie zasoby stylu wskazują nowy katalog.
18. Przeniesiona paczka wczytuje identyczne profile i przykłady.
19. Zmiana treści profilu w kopii zmienia odcisk.
20. Publiczny placeholder nie pozwala aktywować produkcyjnego kontekstu.
21. Wskazanie testowego konta pozwala podłączyć preset w kopii.
22. Zapisany testowy wskaźnik daje się odczytać z właściwym odciskiem.
23. Odłączenie usuwa testową aktywację.
24. Wszystkie sześć pobranych feedów przechodzi parser używany przez silnik.

Parser bota przyjął odpowiednio 30, 19, 19, 30, 48 i 9 wpisów dla
FTC, CMA, BIG, Pluralistic, EFF i iFixit. Różnice względem liczby
surowych elementów XML wynikają z filtrowania tytułów. Te liczby
opisują pojedynczy odczyt, nie częstotliwość przyszłych publikacji.

**Identyfikacja sprawdzonego wariantu**

Odcisk paczki obliczony przez obecny loader:

```text
1e79f482187807ba8ff04b120466a4a1fc7926b2caabc78755324f7bd914c73f
```

SHA-256 plików silnika z użytej kopii:

| Plik | SHA-256 |
|---|---|
| `agent-v2/preset.py` | `ef26f58115d72e184345f3431512afa67ac64410c209902c0f5f4d1491325b42` |
| `agent-v2/config.py` | `cdbcc8dfb5e1a2ae590f9a13dadec560d11f257320c05adec4539b2d99e73ce7` |
| `agent-v2/konfiguracja.py` | `ab03cdef9ce770c6b83a1a1fd8b096e2131b2827d7fd4122a2b86c665651ea4d` |

Przy końcowym porównaniu pliki Pythona w repozytorium odpowiadały
kopii użytej w testach. Równolegle istniejące zmiany projektu nie
zostały cofnięte ani nadpisane przez przygotowanie presetu.

**Czego wynik nie dowodzi**

Nie zmierzono CTR, płatnych subskrypcji, faktycznego miesięcznego
rachunku ani jakości tekstu wyprodukowanego przez skonfigurowane API.
Nie potwierdzono dostępności modeli na koncie operatora. Sprawdzono
zgodność z kodem i kompletność zasobów, a próbki redakcyjne przygotowano
oddzielnie. Ocena pierwszych tekstów jest opisana w `OCENA_JAKOSCI.md`.

Testy nie wdrażają napraw wspólnego Chrome, nazw usług ani globalnego
rachunku kilku instancji. Warunki poprawnego uruchomienia pozostają
opisane w README. Dokument START nie jest automatycznym wsadem banku.

Paczka publiczna jest dopuszczona osobnym wyjątkiem `.gitignore`.
Prywatny preset `nia` nadal pozostaje ignorowany. Zmiana `.gitignore`
nie dotyczy żadnych kluczy, cookies lub katalogów runtime.

Dodano odpowiadający temu wyjątek nazwy `hidden-bill` w regule ścieżek
`narzedzia/audyt.py`. Kontrola uchwytu wszystkich śledzonych presetów
pozostaje wspólna, bez wyjątku dla prawdziwego konta. Osobno sprawdzono,
że reguły nadal odrzucają katalogi `nia`, `hidden-bill-local` i
`hidden-bill-other`, wskaźnik aktywacji, dane instancji, `.env`, sesję
oraz bazę. Pełnego audytu generującego dokumentację nie uruchamiano;
wykonano kontrolę jego reguł dotyczących dodawanej paczki.
