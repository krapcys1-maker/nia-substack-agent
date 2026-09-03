# agent-v2 — architektura

Jedna zasada nadrzędna, z której wynika reszta:

> **Prostsze i działające bije bogatsze i zepsute.**
> Jeśli jakaś warstwa nie zapobiegła realnej stracie, nie ma jej tutaj.

Stary agent miał sześć płatnych etapów, z których każdy mógł zabić łańcuch,
i każdy limit przypięty w trzech do ośmiu miejscach. Tu jest jeden proces,
jeden limit w jednym miejscu, i awaria oznacza „uruchom ponownie".

---

## Kształt

```
run.py  →  jeden proces, sześć kroków po kolei, w pamięci
```

```
 1. skaut tematów        Claude     ~0.10 USD   6 tematów
 2. ocena wykonalności   DeepSeek   ~0.001 USD  odsiew przed drogim krokiem
 3. dyskoveria źródeł    Claude      ~0.65 USD  10 kandydatów + wyszukiwanie
 4. pobranie             HTTP        0 USD      równolegle, tolerancyjnie
 5. klasyfikacja źródeł  DeepSeek   ~0.002 USD  pierwotne / wtórne / odpad
 6. synteza              Claude      ~0.20 USD  karta dowodowa
 7. pisanie              Claude      ~0.19 USD  artykuł
 8. recenzja + bramki    Claude      ~0.20 USD  rozliczenie zdań
 9. zapis                            0 USD      SQLite + plik .md
```

Razem **~1,35 USD** za artykuł. Bez ponowień, bez zgód, bez lease.

### Co się dzieje, gdy coś padnie

Proces kończy się z kodem błędu i wypisuje, na czym stanął. **Nie ma stanu do
posprzątania** — nie ma zadań w kolejce, nie ma dzierżawy do wygaśnięcia, nie
ma zgody do skonsumowania. Uruchamiasz od nowa.

To jest cała różnica wobec starego systemu, gdzie jedno utknięte zadanie
blokowało wszystko na 30 minut i wymagało reapera.

---

## Dane

Jedna baza `data/agent-v2.db`, **cztery tabele**, zero triggerów.

```sql
runs      -- jeden wiersz na uruchomienie: kiedy, status, koszt, na czym stanęło
calls     -- jedno wywołanie modelu: dostawca, model, tokeny, koszt, cel
articles  -- gotowy artykuł: tytuł, treść, karta źródłowa, ocena, status
sources   -- co znaleziono i pobrano: url, klasa, czy się udało
```

Bez migracji z drabiną wersji. Schemat powstaje z `CREATE TABLE IF NOT EXISTS`
przy starcie. Zmiana schematu = zmiana tego pliku.

**Czego celowo nie ma:** trwałych intencji, odcisków, zgód, deklaracji
zdolności, kwalifikacji, dzierżaw, kolejki zadań, indeksów unikalnych na
aktywnych zadaniach, `CHECK`-ów przypinających limity, triggerów append-only.

Każda z tych rzeczy wywaliła produkcję starego agenta 15 sierpnia.

---

## Pieniądze

Jeden moduł `budget.py`, jedna funkcja przed każdym wywołaniem.

```python
budget.check(estimated_usd)   # rzuca, jeśli dzienny/miesięczny limit przekroczony
budget.record(call)           # po wywołaniu: do tabeli calls i do CSV
```

| limit | wartość |
|---|---|
| dzienny | 5 USD |
| miesięczny | 40 USD |
| **tryb budowy** | `AGENT_V2_NO_LIMIT=1` — bez limitów, żeby nie hamować stawiania |

Nie ma rezerwacji przed wywołaniem ani rozliczania po. Stary system miał to
i **faktycznie uratowało pieniądze** przy zabijanych procesach — ale kosztowało
tabelę `provider_attempts`, ośmiostanowy automat i ścieżkę rekoncyliacji.

Tutaj kompromis jest świadomy: jeśli proces zginie w połowie wywołania, koszt
tego wywołania **nie trafi do logu**. Tracimy dokładność zapisu w rzadkim
przypadku, zyskujemy brak całej warstwy. Limit dzienny 5 USD ogranicza szkodę
z definicji.

---

## Jakość — to zostaje, bo zarobiło na siebie

Jedyna warstwa przeniesiona ze starego agenta w całości.

**Bramki (9 reguł)** — pokrycie dowodowe, niepoparte twierdzenia, zmyślone
przeżycia, styl, długość, zgodność z briefem, tytuł kontra treść.

**Reviewer** rozlicza **każde zdanie** i przypisuje mu klasę: fakt oparty na
dowodach / wnioskowanie / proza. Fakt bez dowodu blokuje artykuł.

**Podłogi deterministyczne** porównują tekst z **korpusem**, nie z alfabetem:
liczba spoza korpusu, powołanie na nieistniejące badanie, zmyślone przeżycie.

**19 testów kontradowodowych** — artykuły, które MUSZĄ zostać odrzucone.
Stary agent miał 2800 testów sprawdzających, czy dobry tekst przechodzi,
i ani jednego sprawdzającego, czy zły wylatuje.

---

## Testy

**Mało, ale każdy dotyka rzeczywistości.**

| rodzaj | ile | co sprawdza |
|---|---|---|
| kontradowodowe | ~19 | zły artykuł zostaje odrzucony |
| zgodności | ~5 | prompt zgadza się z walidatorem, termin z sufitem |
| live po każdym etapie | 1 na etap | czy działa naprawdę |

**Nie piszemy testów na atrapach.** Atrapa opisuje świat, który sobie
wyobraziliśmy; płacimy za ten prawdziwy.

---

## Autonomia

Bez zgód wewnętrznych. Agent decyduje sam o temacie, źródłach, treści i ocenie.

**Jedyna granica: nic nie wychodzi na zewnątrz.** Publikacja, komentarz,
polubienie — nie istnieją w kodzie i nie powstaną bez osobnej decyzji
właściciela. Dopóki ich nie ma, „w pełni autonomiczny" znaczy: sam robi
artykuł do szuflady.

Limity redakcyjne (4 artykuły/mies., 5 notek/dzień, 15–20 komentarzy/dzień)
to jedna tabela liczb w `budget.py`, egzekwowana w jednym miejscu.

---

## Czego ta architektura NIE rozwiązuje

Uczciwie, żeby nie było niespodzianek:

1. **Blokady hostów.** eCFR i część stron rządowych odmawiają automatom.
   Wykrywamy to i nie liczymy jako źródło — ale nie obchodzimy. Część tematów
   będzie przez to nieosiągalna.
2. **Monokultura źródeł.** Skaut kierowany na „instytucja + darmowe HTML +
   wpuszcza boty" zbiega do `gov.uk`. Prompt musi wymuszać różnorodność typów
   instytucji, inaczej konto będzie gazetą o brytyjskich przepisach.
3. **Utrata kosztu przy zabiciu procesu.** Świadomy kompromis, opisany wyżej.
4. **Brak etapów 5–7.** Publikacja, notki, komentarze, statystyki nie istnieją.

---

## Kolejność budowy — najpierw artykuł, potem reszta

Limity redakcyjne obejmują trzy rodzaje treści, ale **buduj je po kolei, nie
naraz**:

| kolejność | co | stan |
|---|---|---|
| **1** | **artykuły** — 4/miesiąc | to budujesz teraz, cały ten dokument o tym |
| 2 | notki — 5/dzień | dopiero po trzech udanych artykułach |
| 3 | komentarze — 15–20/dzień | ostatnie, i najostrożniej |

**Dlaczego w tej kolejności.** Artykuł jest najdroższy i najtrudniejszy, więc
jeśli zadziała, notka jest jego uproszczeniem — ten sam styl, ten sam reviewer,
krótszy tekst, jedno źródło zamiast siedmiu. Odwrotnie się nie da: notki nie
nauczą Cię niczego o pokryciu dowodowym.

**Komentarze na końcu i z osobną ostrożnością.** Artykuł, który wyjdzie słabo,
leży w szufladzie. Komentarz jest odpowiedzią konkretnej osobie na jej tekst
i **nie da się go cofnąć w oczach tej osoby**. Zanim je zbudujesz, poproś
właściciela o osobną decyzję i pokaż mu kilkanaście wygenerowanych przykładów
do oceny, zanim którykolwiek gdziekolwiek trafi.

Notki i komentarze **nie mają jeszcze własnego stylu potwierdzonego produkcją**
— jest `NOTES_STYLE_PROFILE_V1.md`, ale żadna notka nigdy nie powstała. Traktuj
ten profil jako punkt wyjścia, nie jako sprawdzony wzorzec.
