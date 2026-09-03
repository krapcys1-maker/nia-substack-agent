# Te testy KOSZTUJĄ PIENIĄDZE

Wszystko w tym katalogu robi prawdziwe wywołania API. Nie uruchamiaj ich
pętlą razem z resztą — katalog wyżej jest darmowy i można go puszczać
bez zastanowienia, ten nie.

Powstał, bo raz to zrobiłem: wrzuciłem wszystkie testy do jednego katalogu,
puściłem pętlę na serwerze i zawiesiła się na `test_bibliotekarz`, który
czekał na model. Ktokolwiek uruchomiłby „wszystkie testy", zapłaciłby za nie
bez ostrzeżenia.

| plik | co robi | orientacyjny koszt |
|---|---|---|
| `test_integracja.py` | **PEŁNY PŁATNY PRZEBIEG DNIA** z przerwami 45–90 min | godziny pracy, kilka USD |
| `test_notki_ab.py` | notki na DeepSeeku i Fable, ten sam materiał | ~$0,95 |
| `test_notki_szeroki_material.py` | trzy notki na Fable z szerokiego materiału | ~$0,70 |
| `test_notki_z_banku.py` | trzy notki z banku plus weryfikacja | ~$0,10 |
| `test_warto.py` | bramka ciekawości na pięciu prawdziwych kartach | ~$0,08 |
| `test_bibliotekarz.py` | grupowanie całego banku fragmentów | ~$0,06 |
| `test_style.py` | cztery warianty okładki | ~$0,16 |

## Jak je uruchamiać

Pojedynczo, świadomie, z korzenia repozytorium:

```
python agent-v2/tests/platne/test_warto.py
```

Większość z nich to **nie są testy zerojedynkowe** — wypisują materiał do
oceny przez człowieka i miary, które da się policzyć. Ocena jakości tekstu
należy do właściciela, nie do asercji.

## Wyjątek, o którym trzeba pamiętać

`test_integracja.py` odpala pełny przebieg dnia z **prawdziwymi** przerwami
45–90 minut między notkami. Przy starych odstępach (10–25 min) był wykonalny;
teraz chodzi godzinami. Trzeba mu podmienić `config.ODSTEPY`, tak jak
podmienia `OKNO_PUBLIKACJI_ET`. **Do tego czasu pełny przebieg dnia nie jest
pokryty żadnym testem** i jest to największa niepokryta część systemu.
