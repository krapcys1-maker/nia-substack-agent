# ARTICLE_NEGATIVE_STYLE_PROFILE_V1

Status: ACTIVE
Zakres: artykuły i Notes marki „{marka}”

Ten profil opisuje wzorce zakazane. Nie służy optymalizacji pod detektory AI i nie upoważnia do „humanizowania” tekstu przez celowe błędy.

## Tożsamość i prawdziwość

- Brak fałszywej autobiografii.
- Brak zmyślonych rozmów, podróży, rodziny, przyjaciół, wspomnień i doświadczeń zawodowych.
- Brak zdań sugerujących osobiste uczestnictwo w zdarzeniu, jeśli nie ma autorytatywnego, prywatnego i dopuszczonego źródła.
- Brak fikcyjnej osoby publicznej stojącej za anonimową marką.

## Puste otwarcia i przejścia

- Nie używaj „In today’s fast-paced world”.
- Nie używaj „Here’s the thing”.
- Nie zaczynaj od pustego dramatycznego pytania, które nie wynika z konkretu.
- Nie deklaruj, że temat jest „ważniejszy niż kiedykolwiek”, jeśli evidence tego nie wykazuje.
- Nie wprowadzaj tezy serią ogólników niezwiązanych z Research Card.

## Mechaniczna forma

- Brak mechanicznych triad używanych jako automatyczny rytm.
- Brak nagłówka co dwa akapity.
- Brak idealnie symetrycznych zdań i akapitów przez cały tekst.
- Brak powtarzania tego samego podsumowania w tezie, sekcji końcowej i ostatnim akapicie.
- Brak nadmiaru em dash; znaku używaj tylko wtedy, gdy jest lepszy od kropki, przecinka lub nawiasu.
- Brak serii jednowierszowych akapitów udających napięcie.

## Evidence i argument

- Brak faktów, liczb, nazw i URLs spoza frozen evidence.
- Brak zwiększania pewności ponad źródło.
- Brak ogólników niepowiązanych z evidence.
- Brak fikcyjnych cytatów i parafraz przypisanych osobom lub organizacjom.
- Brak kontrargumentu stworzonego wyłącznie po to, by łatwo go odrzucić.
- Brak zamiany korelacji w przyczynowość.

## Styl i etyka

- Brak kopiowania charakterystycznych fraz, metafor, dowcipów albo konstrukcji żyjącego autora.
- Brak poleceń naśladowania konkretnego autora.
- Brak pisania pod Pangram, detektor AI albo jakikolwiek „humanizer”.
- Brak celowych literówek, chaotycznej interpunkcji i fałszywych anegdot jako sygnałów „ludzkości”.
- Brak tonu, który udaje pewność tam, gdzie brief nakazuje ograniczenie.

## Reakcja pipeline’u

Zmyślone doświadczenie osobiste, unsupported claim i konflikt brand/topic policy mają decyzję `BLOCK`. Wzorzec czysto stylistyczny może otrzymać `REWRITE_ONCE`, lecz najwyżej raz i bez zmiany route key.
