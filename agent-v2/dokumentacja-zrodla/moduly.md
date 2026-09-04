
### `run.py` — rozdzielnik — ścieżka artykułu i ścieżka dnia

2845 wierszy, 26 funkcji na poziomie modułu, 1 klas

| funkcja | co robi |
|---|---|
| `_utf8_stdout()` *(wewn.)* | Konsola Windows domyślnie cp1252 i wywala się na polskich znakach. |
| `cached(stage, produce, use_cache)` | Zapisuje wynik etapu i oddaje go z dysku zamiast płacić drugi raz. |
| `odmow_publikacji_z_kopii(wyslij)` | Kopia testowa nie ma prawa nic opublikowac. Nigdy. |
| `zajmij_zamek()` | Nie pozwala dwóm przebiegom działać naraz. |
| `opis_celu(cel)` | Co wiedzielismy o celu w chwili pisania — do dziennika. |
| `zostal_czas(na_co, potrzeba_s)` | Czy zdazymy jeszcze cokolwiek zrobic przed koncem czasu przebiegu. |
| `_pod_rzad_w_bloku(co, na_co)` *(wewn.)* | Ile porazek pod rzad naliczyl TEN blok, odkad sie zaczal. |
| `rytm(co, na_co, stan)` | Przerwa MIEDZY dwoma dzialaniami tego samego rodzaju. |
| `zmiesci_sie(rodzaj, ile, udzial)` | Ile z zaplanowanych dzialan NAPRAWDE zmiesci sie w czasie przebiegu. |
| `ile_przebiegow_zostalo(conn)` | Ile przebiegow dnia jeszcze bedzie, wliczajac biezacy. |
| `_slug(tekst)` *(wewn.)* | Nazwa do porownywania: same litery i cyfry ASCII, malymi. |
| `_slug_hosta(host)` *(wewn.)* | Pierwszy czlon adresu jako slug: `www.imienazwisko.com` -> `imienazwisko`. |
| `_reakcje_z_dziennika()` *(wewn.)* | Jeden przebieg po dzienniku, dwie odpowiedzi o tych samych ludziach. |
| `kogo_juz_dotknelismy()` | Slugi nazw ludzi, ktorzy zareagowali na NASZA tresc — z dziennika. |
| `nasi_czytelnicy()` | Uchwyty ludzi, ktorzy JUZ nas czytaja — z `czytelnicy.jsonl`. Tylko odczyt. |
| `reagujacy_jako_cele()` | Ludzie, ktorzy zareagowali na nasza tresc, jako CELE WPROST. Zero sieci. |
| `_przeplot(pierwsza, druga)` *(wewn.)* | Na przemian z dwoch list; gdy jedna sie konczy, druga idzie dalej. |
| `cele_wedlug_pierwszenstwa(historia)` | Hosty do zaczepienia, w kolejnosci pierwszenstwa. Zero sieci. |
| `powod_pustej_puli(rachunek)` | Zdanie do dziennika, gdy po odsianiu nie zostal nikt. |
| `kogo_juz_subskrybujemy()` | Uchwyty, na ktore subskrypcja NIE MA JUZ CO wysylac. Z dziennika, bez sieci. |
| `czy_juz_subskrybujemy(host, zamkniete, pamiec)` | Czy ten HOST wskazuje konto, na ktore nie ma juz po co wchodzic. |
| `dzien(conn, run_id, wyslij)` | Jeden dzień pracy konta: notki, komentarze, odpowiedzi, polubienia. |
| `_sygnal_ma_zostawic_slad()` *(wewn.)* | Zamienia SIGTERM na wyjatek, zeby przebieg zdazyl sie zapisac. |
| `main()` | — |
| `_done(conn, run_id, stage)` *(wewn.)* | — |
| `_summary(conn, run_id)` *(wewn.)* | — |

### `stages.py` — wszystkie etapy myślowe; nie dotyka przeglądarki

7401 wierszy, 135 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_na_kanal(nazwa)` *(wewn.)* | Wszystko, co ta funkcja zaplaci, ksieguje sie na kanal `nazwa`. |
| `_blok_przykladow(klucz, gdy_pusto)` *(wewn.)* | Przyklady z niszy jako lista punktow — albo polecenie, gdy ich nie ma. |
| `_pola_wspolne()` *(wewn.)* | Nisza, marka i jezyk — czytane z configu przy KAZDYM wywolaniu. |
| `_prompt(name, **fields)` *(wewn.)* | — |
| `recent_angles(conn, limit)` | Ostatnie kąty redakcyjne — wejście do reguły różnorodności. |
| `tematy_do_porownania(conn, limit)` | Poprzednie artykuly w postaci NADAJACEJ SIE DO POROWNANIA. |
| `review(conn, run_id, card, draft)` | Etap 8 — recenzja: rozliczenie kazdego zdania (DeepSeek V4 Pro). |
| `ocen_forme(conn, run_id, draft)` | Obserwacja formy: beaty, eskalacja, moment przyłapania, znajomość otwarcia. |
| `ostatnie_uwagi(ile)` | Co zarzucono OSTATNIM artykulom — do promptu pisarza. |
| `poprzednie_teksty(ile, pomin_tresc)` | Treści kilku ostatnich artykułów — materiał dla bramki ODCISK_FORMY. |
| `_nazwa_zrodla(conn, url)` *(wewn.)* | Nazwa źródła zamiast gołego adresu. |
| `save(conn, run_id, topic, card, draft, status, blocked_by, notes)` | Etap 9 — zapis. Artykuł do szuflady: baza + plik .md. |
| `karta_dla_pisarza(card, teraz)` | Karta bez zastrzezenia, ktorego nie wolno opublikowac. |
| `wstaw_date_zrodel(tekst, card)` | Stopka z data zrodel pisana PRZEZ KOD, nie przez model. |
| `write(conn, run_id, card, glebokosc)` | Etap 7 — artykuł (Claude). To jest produkt. |
| `_ile_reakcji(k)` *(wewn.)* | „(reakcji: N)" TYLKO wtedy, gdy zrodlo to pole w ogole wypelnia. |
| `_po_rowno_ze_zrodel(komentarze, ile)` *(wewn.)* | Wycinek listy, ktory NIE MOZE zaglodzic zadnego miejsca rozmowy. |
| `wybierz_do_odpowiedzi(conn, run_id, komentarze)` | Komu odpisac, gdy komentarzy jest wiecej niz kilka. |
| `reply_to(conn, run_id, comment, evidence)` | Odpowiedź na komentarz pod własną treścią — do szuflady. |
| `plan_tygodnia(dzien_artykulu)` | Harmonogram tygodnia: co i kiedy wychodzi. |
| `grafika(conn, run_id, draft, sciezka_artykulu)` | Nagłówek graficzny artykułu. |
| `_wiek_konta_w_dniach(conn)` *(wewn.)* | Ile dni działa to konto — liczone od pierwszego przebiegu w bazie. |
| `budzet_dnia(conn)` | Ile czego agent może dziś zrobić — losowane z widełek, nie stałe. |
| `_zapisz_budzet_dnia(dzien, budzet, rozbieg)` *(wewn.)* | Zapisuje, ile agent SOBIE ZALOZYL na ten dzien. |
| `sesje_dnia()` | Rozkłada dzień na kilka posiedzeń zamiast jednego ciągu. |
| `losuj_odstep(co)` | Losuje przerwę, ale jej NIE odsypia. |
| `odczekaj(co, ile)` | Przerwa po działaniu, dobrana do tego, ile ono zajmuje CZLOWIEKOWI. |
| `_klucz_faktu(tekst)` *(wewn.)* | Odcisk faktu odporny na przestawienie słów i inną liczbę w tym samym zdaniu. |
| `tekst_faktu(x)` | Fakt bywa slownikiem (`{"fact": ..., "url": ...}`), a bywa samym zdaniem. |
| `wczytaj_zuzyte()` | — |
| `zapisz_zuzyte(nowe)` | Pamięć zużytych ciekawostek — poza bazą, bo budżet to cztery tabele. |
| `wybierz_cele(conn, run_id, posty)` | Które posty z kanału zasługują na komentarz. |
| `zaczyn_z_kanalow(ile)` | Tematy, o ktorych mowi sie w tym tygodniu — do promptu, nie do cytowania. |
| `_rdzen_wydarzenia(w)` *(wewn.)* | Klucz zdarzenia: posortowane slowa rdzenia, zeby ta sama premiera |
| `_nowe_wydarzenia(wydarzenia)` *(wewn.)* | Ktore z tych zdarzen sa NOWE — czyli nie dobieralismy juz o nich materialu. |
| `_zapamietaj_wydarzenia(nowe, znane, ile)` *(wewn.)* | Zapisuje, ze o tych zdarzeniach material JUZ WROCIL. |
| `_przebiegi_z_bankiem_dzis(conn)` *(wewn.)* | Ile PRZEBIEGOW dobieralo dzis material do banku. |
| `_polecenie_premiery(wydarzenia, ile)` *(wewn.)* | Polecenie o premierze do promptu ciekawostek — albo PUSTY NAPIS. |
| `znajdz_ciekawostki(conn, run_id, ile)` | Materiał na notki w dni bez artykułu. |
| `kuplet_korygujacy(tekst)` | Czy tekst uzywa ruchu „nie X. Y." — zaprzeczenie, potem poprawka. |
| `zdania_z_tikiem(tekst)` | TE SAME trzy postacie tiku, ale oddane jako ZDANIA, nie jako „tak/nie". |
| `ostatnie_otwarcia(rodzaj, ile)` | Pierwsze slowa ostatnich notek — zeby kolejna nie zaczela sie tak samo. |
| `wiek_zrodla_w_dniach(data_zrodla, teraz)` | Ile dni ma zrodlo. None, gdy daty nie da sie odczytac. |
| `nazywa_wersje(tekst)` | Czy zdanie nazywa konkretna wersje produktu. Zwraca ja albo pusty napis. |
| `swiezosc_karty(card, teraz)` | Ile lat ma material, na ktorym stanie artykul. Zwraca uwagi, nie werdykt. |
| `swiezosc_faktu(fakt, teraz)` | Czy ten fakt nadaje sie do wystawienia DZISIAJ. |
| `ostatnie_notki(ile)` | TRESCI ostatnich wystawionych notek — zeby nie napisac drugi raz tego samego. |
| `_notki_z_dziennika(kawalek)` *(wewn.)* | Teksty UDANYCH notek z podanego kawalka dziennika, w kolejnosci zapisu. |
| `_sygnatura_rdzeni()` *(wewn.)* | Odcisk SPOSOBU liczenia rdzeni, nie tresci. |
| `_wczytaj_skrot_notek()` *(wewn.)* | Skrot z dysku albo pusty. Uszkodzony plik to pusty skrot, nie awaria. |
| `pamiec_wystawionych()` | Odciski WSZYSTKICH wystawionych notek. Pamiec nie ma konca. |
| `_przytnij_pamiec(odciski)` *(wewn.)* | Zamienia odciski na zbiory i honoruje `config.PAMIEC_NOTEK`. |
| `_zapisz_skrot_notek(odciski, bajtow, glowa, glowa_bajtow, sygnatura)` *(wewn.)* | Zapisuje skrot. NIGDY nie przerywa dnia. |
| `_opis_typu(note_type)` *(wewn.)* | Opis typu, a przy MYSLI takze PRZYDZIELONY ksztalt. |
| `note(conn, run_id, note_type, evidence, link, note_form, etap)` | Jedna notka danego typu i danej FORMY — do szuflady. |
| `_pola_ksztaltu(ksztalt, pomin)` *(wewn.)* | Nazwy pol z kontraktu na odpowiedz, bez klucza opakowujacego. |
| `zakwestionuj_promocje(url, powod)` | Artykul, ktorego notka promujaca odpadla na sprawdzeniu faktow. |
| `zapamietaj_niewystawiony(sciezka, powod)` | Zapisuje, ze gotowy artykul lezy na dysku i nie poszedl w swiat. |
| `niewystawiony_artykul()` | Artykul czekajacy na ponowna probe, albo None. NIGDY nie rzuca. |
| `odnotuj_probe_artykulu(powod)` | Podbija licznik prob i oddaje nowa wartosc. Zero, gdy znacznika nie ma. |
| `zapomnij_niewystawiony()` | Tekst jest publiczny — znacznik znika. |
| `zapisz_do_promocji(url, tytul, tekst)` | Zapisuje opublikowany artykul do promowania przez kolejne dni. |
| `wczytaj_promocje()` | — |
| `artykul_do_promocji()` | Artykul, ktory dzis czeka na notke promujaca — najwyzej JEDNA na dobe. |
| `odhacz_promocje(url, tekst)` | Odnotowuje, ze artykul dostal dzis swoja notke promujaca — I CO W NIEJ BYLO. |
| `_slowa(tekst)` *(wewn.)* | Znaczace slowa tekstu, obciete do rdzenia. |
| `_zderzenie(x, y, min_wspolnych, prog)` *(wewn.)* | To samo pytanie co `_o_tym_samym`, ale na GOTOWYCH rdzeniach. |
| `nazwy_wlasne(tekst)` | Nazwy wlasne i identyfikatory z tekstu, sprowadzone do jednej postaci. |
| `wspolna_nazwa(a, b, korpus, maks_czestosc)` | Nazwa wlasna, ktora wystepuje w OBU tekstach i jest rzadka w korpusie. |
| `_o_tym_samym(a, b, min_wspolnych, prog)` *(wewn.)* | Czy dwa teksty mowia o tej samej rzeczy. |
| `teksty_ostatnich_notek(ile)` | Tresci ostatnich notek — do porownania po NAZWACH WLASNYCH. |
| `wybierz_material(zapas, unikaj, wczesniej, teksty)` | Bierze fakt, ktory NIE jest o tym samym, co juz dzis wystawiamy. |
| `notki_dnia(conn, run_id, dzien_artykulu, karta, ciekawostki, link_artykulu, ile, od)` | Do pieciu notek z dziennego planu, kazda z innego materialu. |
| `ocen_restack(conn, run_id, notka)` | Czy podac te notke dalej i z jakim zdaniem. |
| `_podloga_z_pamieci(tekst)` *(wewn.)* | Dwie podlogi, ktore dzialaja BEZ karty dowodowej. |
| `_otwarcie_formulka(zdanie)` *(wewn.)* | Czy zdanie zaczyna sie od zapowiedzi ruchu zamiast od samego ruchu. |
| `sprawdz_fakty(conn, run_id, post)` | Szuka faktów do komentarza, zamiast pozwolić modelowi pisać z pamięci. |
| `bez_wstrzykniecia(tekst, wlasny_adres_ok)` | Czy w naszym tekscie nie ma sladu cudzych POLECEN. |
| `_status_twierdzenia(c)` *(wewn.)* | Status twierdzenia, znormalizowany. NIEZNANA ETYKIETA ZNACZY `unverified`. |
| `zweryfikuj(conn, run_id, tekst, kontekst)` | Sprawdza to, co model NAPISAŁ — nie to, czego szukał przed pisaniem. |
| `_zapora_notki(tekst)` *(wewn.)* | Pusty napis, gdy tekst notki przechodzi zapory. Inaczej powod. |
| `_zapora_komentarza(tekst)` *(wewn.)* | To samo dla komentarza — ale komentarz ma zapore o jedna wiecej. |
| `_liczby_zarzutu(c)` *(wewn.)* | Liczby z zarzutu, znormalizowane — po nich rozpoznajemy TEN SAM fakt. |
| `_slowa_zarzutu(c)` *(wewn.)* | Slowa tresciowe z samego twierdzenia — drugi sygnal tozsamosci. |
| `_adres_zarzutu(c)` *(wewn.)* | — |
| `_ten_sam_zarzut(a, b)` *(wewn.)* | Czy dwa zarzuty mowia o tym samym fakcie. ZACHOWAWCZO, i to celowo. |
| `napraw_obalone(conn, run_id, tekst, audyt)` | Poprawia zdanie, ktoremu zapis przeczy. Nie wycina go i nie blokuje tekstu. |
| `comment_on(conn, run_id, post, fakty)` | Komentarz do cudzego posta — do szuflady. |
| `fallback_card(question, evidence)` | Karta złożona z dowodów bez modelu — gdy synteza padnie. |
| `synthesis(conn, run_id, question, evidence)` | Etap 6 — karta dowodowa (DeepSeek V4 Pro). |
| `classify(conn, run_id, question, corpus)` | Etap 5 — klasyfikacja i wyciąg fragmentów (DeepSeek). |
| `_dobierz_przegladarka(conn, run_id, brakujace, juz_mamy)` *(wewn.)* | Drugie podejscie do stron, ktore zwyklemu pobieraniu daly pusty szkielet. |
| `fetch(conn, run_id, sources)` | Etap 4 — pobranie stron. Zwykły HTTP, żadnego modelu, 0 USD. |
| `_host(url)` *(wewn.)* | — |
| `hosty_ktore_nigdy_nie_dzialaly(conn, min_prob)` | Hosty, ktore probowalismy >=2 razy i ANI RAZU sie nie udalo. |
| `discovery(conn, run_id, question, recent_domains, tylko_pierwotne)` | Etap 3 — dyskoveria zrodel (DeepSeek V4 Pro + web_search dostawcy). |
| `feasibility(conn, run_id, topics)` | Etap 2 — tani odsiew przed drogą dyskoverią (DeepSeek). |
| `podsumowanie_dzialan(dni)` | Ile czego WYSZLO w ostatnich `dni` dniach, wobec normy z configu. |
| `powody_porazek(dni)` | Dlaczego dzialania sie NIE UDALY — pogrupowane, najczestsze pierwsze. |
| `_powod_przegranej(klucz_zwyciezcy, klucz_tematu)` *(wewn.)* | Ktory skladnik klucza sortowania ROZSTRZYGNAL, i jakimi wartosciami. |
| `_pisze_do_produkcji(sciezka)` *(wewn.)* | Czy ta sciezka to PRAWDZIWY katalog danych, a nie katalog testu. |
| `zapisz_przegranych(przegrani, run_id)` | Dopisuje do dziennika tematy, ktore NIE wygraly, z powodem przegranej. |
| `pick_topic(topics, assessments, run_id, wczesniejsze)` | Wybiera temat leksykograficznie wedlug dziewieciu kryteriow. |
| `scout(conn, run_id, count)` | Etap 1 — skaut tematow (DeepSeek V4 Pro). |
| `bank_fragmentow(conn, dni)` | Nieuzyte fragmenty ze wszystkich artykulow — zaplacone i nieprzeczytane. |
| `bibliotekarz(conn, run_id, bank)` | Grupuje bank po MECHANIZMIE. Model proponuje, KOD weryfikuje. |
| `wczytaj_bank_notek()` | Gotowe notki czekajace na swoj moment. Plik, nie tabela — limit czterech |
| `dopisz_do_banku_notek(notki)` | Dokłada notki do banku, pomijajac te, ktore juz tam sa. |
| `wez_z_banku_notek(ile)` | Wyjmuje najstarsze niewykorzystane notki i ZNACZY je jako wyjete. |
| `stan_banku_notek()` | Ile mamy zapasu — do wypisania przy starcie przebiegu. |
| `warto_pisac(conn, run_id, card)` | Etap przed pisarzem: czy jest tu luka, ktora obcy poczuje. |
| `zbierz_pytania(wpisy)` | Wyławia z odpowiedzi czytelnikow te, ktore sa PYTANIAMI, i zapisuje je. |
| `wczytaj_pytania()` | Pula pytan czytelnikow. Uszkodzony plik to pusta pula, nie awaria. |
| `pytania_dla_skauta(ile)` | Najswiezsze pytania czytelnikow, gotowe do wklejenia w prompt skauta. |
| `_to_pdf(odpowiedz, url)` *(wewn.)* | Czy to PDF. Naglowek jest wiarygodniejszy od koncowki adresu. |
| `_tekst_z_pdf(dane, max_stron)` *(wewn.)* | Warstwa tekstowa PDF-a. |
| `bramka_kandydata(k)` | Czy z tego da sie zrobic notke. Sprawdza KOD, nie model. |
| `wczytaj_indeks()` | Indeks kandydatow. Uszkodzony plik NIE udaje juz pustego banku. |
| `_zapisz_indeks(indeks)` *(wewn.)* | Zapis ATOMOWY: najpierw plik obok, potem podmiana jednym ruchem. |
| `_stale_sygnaly(topics, pola)` *(wewn.)* | Ktore z pol mialy TE SAMA wartosc u WSZYSTKICH kandydatow. |
| `_precedens_ok(p)` *(wewn.)* | Czy ten wpis to naprawde precedens, a nie wypelniacz. |
| `_wspolna_kotwica(a, b)` *(wewn.)* | Czy oba zdania mowia o tej samej NAZWIE albo tej samej LICZBIE. |
| `dopisz_kandydatow(kandydaci)` | Przepuszcza kandydatow przez bramke i dokłada do indeksu. |
| `wez_kandydatow(ile)` | Wyjmuje kandydatow gotowych do pisania i ZNACZY ich jako uzytych. |
| `co_zadzialalo(ile)` | NASZE wlasne notki z ZMIERZONYM odbiorem — material dla sedziego banku. |
| `_tabela_odbioru(naj, ile)` *(wewn.)* | Najlepiej i najgorzej przyjete notki, gotowe do wklejenia w prompt. |
| `posortuj_bank(conn, run_id, ile)` | Ustawia bank pomyslow od najmocniejszego i wyrzuca slabe. |
| `_termin_waznosci(dni)` *(wewn.)* | Kiedy ta kandydatura przestaje byc tematem. Data z godzina, w UTC. |
| `_z_obecnej_epoki(k)` *(wewn.)* | Czy ta kandydatura powstala PO ostatniej zmianie tematu konta. |
| `_po_terminie(k)` *(wewn.)* | Czy kandydatura jest juz po swoim terminie przydatnosci. |
| `bank_pelny()` | Czy zapas wystarczy, zeby NIE placic za nowe szukanie. |
| `zwroc_kandydatow(kandydaci)` | Oddaje do puli kandydatow, ktorych ostatecznie NIE uzyto. |
| `stan_indeksu()` | Ile mamy zapasu i ile odsialismy — do wypisania przy starcie. |
| `korpus_fedreg(ile_dokumentow, ile_gestych)` | Preambuly przepisow, w ktorych regulator ODPOWIADA na zastrzezenia. |
| `kandydaci_z_fedreg(conn, run_id, dokument)` | Wyciaga kandydatow z jednej preambuly i oddaje w ksztalcie indeksu. |

### `browser.py` — cała styczność z Substackiem; nie woła modelu

5203 wierszy, 96 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `wlasciwe_konto(page)` | Czy jestesmy na WLASCIWYM koncie tuz przed publikacja. |
| `pod_rzad_nieudanych(rodzaj)` | Ile porazek tego rodzaju poszlo BEZPOSREDNIO po sobie w tym przebiegu. |
| `slad_przebiegu()` | Podsumowanie tego, co ten proces zrobil — do wypisania na koncu. |
| `dopisz_wynik(rodzaj, wynik, **szczegoly)` | Jeden wpis na dzialanie — takze wtedy, gdy sie NIE UDALO, i z powodem. |
| `zapisz_w_dzienniku(rodzaj, **szczegoly)` | Dziennik DZIALAN, nie wywolan modelu. |
| `z_dziennika_dzis()` | Ile komentarzy i polubien poszlo dzis — wedlug naszego zapisu. |
| `naprawde_wyslac(wyslij, co)` | Ostatnie sito przed KAZDYM dzialaniem widocznym publicznie. |
| `zalogowany(context)` | Twarde sprawdzenie: albo jest ciasteczko sesji, albo go nie ma. |
| `dni_do_wygasniecia()` | Ile dni zostało sesji. None, gdy sesji nie ma wcale. |
| `wymagaj_sesji()` | Sprawdza sesję przed pracą i mówi wprost, gdy trzeba się zalogować. |
| `_chrome_odpowiada()` *(wewn.)* | — |
| `uruchom_chrome()` | Otwiera Chrome na trwałym profilu agenta, jeśli jeszcze nie działa. |
| `rozgrzej(context)` | Pozwala Cloudflare wydać zgodę dla adresu, z którego akurat działamy. |
| `plaski(tekst)` | Tekst sprowadzony do znakow, ktore SAMI piszemy — do POROWNYWANIA. |
| `api_json(page, sciezka, baza)` | Czyta API WCHODZĄC na adres, zamiast wołać `fetch` ze strony. |
| `podlacz_sie()` | Podłącza się do Chrome'a, którego uruchomił i zalogował WŁAŚCICIEL. |
| `sprawdz_sesje()` | Czy Chrome właściciela jest zalogowany i co agent w nim widzi. |
| `sprawdz_serwer()` | Odpowiada na JEDNO pytanie: czy zapisana sesja żyje z adresu tego serwera. |
| `zaloguj()` | Otwiera prawdziwe okno przeglądarki i czeka, aż właściciel się zaloguje. |
| `rozpoznanie()` | Sprawdza, czy agent umie się poruszać po zalogowanym koncie. |
| `_plaskie(galaz)` *(wewn.)* | Rozwija gałąź wątku do płaskiej listy komentarzy. |
| `_kiedy(c)` *(wewn.)* | — |
| `ile_dzis_wystawione()` | Ile notek, komentarzy i polubien poszlo dzisiaj. |
| `statystyki_pozycji(pozycje)` | Pobiera statystyki NASZYCH tresci — jedna przegladarka na cala liste. |
| `_ludzie_z_zakladki_ze_stanem(page)` *(wewn.)* | Kto jest na tej zakladce ORAZ czy zakladke w ogole udalo sie odczytac. |
| `_ludzie_z_zakladki(page)` *(wewn.)* | Sama lista ludzi z zakladki. Dla wolajacych, ktorych stan nie obchodzi. |
| `kto_nas_czyta(page)` | KTO nas obserwuje i subskrybuje — imiennie i z data. |
| `zapisz_czytelnikow(page)` | Zrzut listy czytelnikow do pliku, jeden wiersz na wywolanie. |
| `kogo_obserwujemy()` | Kogo juz obserwujemy — Z DYSKU, BEZ SIECI. |
| `_zapisz_kogo_obserwujemy(pamiec)` *(wewn.)* | Nigdy nie przerywa dzialania — to pamiec pomocnicza, nie warunek pracy. |
| `zapamietaj_obserwowanego(uchwyt, host)` | Dopisuje JEDNEGO do pamieci — po udanej obserwacji albo po zastaniu |
| `czy_juz_obserwujemy(host, pamiec)` | Czy ten HOST wskazuje kogos, kogo juz obserwujemy. Bez sieci. |
| `odswiez_kogo_obserwujemy(page)` | Przepisuje pamiec ze strony `/@my/following`. Wymaga OTWARTEJ sesji. |
| `zapisz_wzrost_konta(profil)` | Ilu nas czyta DZISIAJ — jedna linia na pomiar, historia zostaje. |
| `_wiersze_zrodel(dane)` *(wewn.)* | Lista pozycji z odpowiedzi o zrodlach — niezaleznie od klucza. |
| `_cos_w_odpowiedzi(dane)` *(wewn.)* | Czy odpowiedz W OGOLE cos niesie — odroznia „pusto" od „nie wiem". |
| `_suma_pola(wiersze, *pola)` *(wewn.)* | Suma pierwszego istniejacego pola po wierszach. |
| `_z_miar(wezel, nazwy)` *(wewn.)* | Liczba z `metrics: [{"name": "Subscribers", "total": 5}, ...]`. |
| `_zapisy_wezla(wezel)` *(wewn.)* | Zapisy z jednej galezi — obojetne, w ktorym z dwoch ksztaltow przyszly. |
| `_z_totali(dane, nazwy)` *(wewn.)* | Liczba z pola `totals` — panel podaje je LISTA, nie slownikiem. |
| `_zapisy_ogolem(dane)` *(wewn.)* | Laczna liczba zapisow z drzewa `growth/sources`, albo `None`. |
| `_zapisy_per_notka(dane)` *(wewn.)* | {numer notki: zapisy} — z dowolnie zagniezdzonego drzewa. |
| `zapisz_zrodla_ruchu(page, dni)` | SKAD naprawde biora sie zapisy — tabela zrodel, jedna linia na odczyt. |
| `_artykuly_z_panelu(page, baza)` *(wewn.)* | Nasze artykuly razem ze statystykami — JEDNYM zapytaniem. |
| `nasze_pozycje_do_pomiaru(page, ile)` | Co wystawilismy i ma wlasny numer — czyli co da sie zmierzyc. |
| `dopisz_skutki()` | Dopisuje do dziennika, CO Z NASZYCH DZIALAN WYNIKLO. |
| `odpowiedzi_na_nasze_komentarze(ile)` | Odpowiedzi na NASZE komentarze zostawione pod CUDZYMI tekstami. |
| `komentarze_pod_artykulami(ile)` | Cudze komentarze pod NASZYMI artykulami, na ktore nie odpisalismy. |
| `nieodpowiedziane(ile)` | Cudze odpowiedzi pod naszymi notkami, na które jeszcze nie odpisaliśmy. |
| `sluchaj_publikacji(page)` | Zbiera kody odpowiedzi na zapytania PUBLIKUJACE. |
| `id_z_odpowiedzi(odpowiedzi)` | Identyfikator notki, ktory Substack oddal przy zapisie. |
| `numer_naszej_notki(page, tekst, prob)` | Numer notki odczytany z NASZEGO PROFILU po jej tresci. |
| `potwierdz_notke(page, tekst, prob)` | Pyta Substacka, czy notka naprawdę wisi na naszym profilu. |
| `_autor_przy_przycisku(przycisk)` *(wewn.)* | Kto napisal wpis, przy ktorym stoi ten przycisk. |
| `_uchwyt_wezla(lokator)` *(wewn.)* | Uchwyt do KONKRETNEGO wezla DOM, albo None. Nie podnosi wyjatku. |
| `_stan_przycisku(uchwyt)` *(wewn.)* | Jak przycisk wyglada — wszystkie sygnaly naraz, sklejone w jeden napis. |
| `potwierdz_polubienie(uchwyt, przed)` | Czy przycisk po klknieciu wyglada inaczej niz przed nim. |
| `polub_w_kanale(ile, wyslij)` | Polubienia w kanale czytelnika. |
| `_klik_na_profilu(handle, napisy, rodzaj, wyslij)` *(wewn.)* | Klika JEDEN konkretny przycisk na cudzym profilu — i tylko jego. |
| `pobierz_subskrybentow()` | Czyta liste subskrybentow z WLASNEGO panelu, wlasna sesja. |
| `zloz_wiersze_subskrybentow(surowe)` | Sklada wiersze z komorek tabeli panelu: adres, typ i data rozpoczecia. |
| `_wiersze_subskrybentow(page)` *(wewn.)* | Czyta komorki tabeli z panelu i oddaje je zlozone. |
| `_pozycje_menu(page)` *(wewn.)* | Teksty pozycji OTWARTEGO menu, w kolejnosci ekranu. Nic nie klika. |
| `_otworz_menu_profilu(page)` *(wewn.)* | Klika kolko „..." w naglowku profilu. Otwarcie menu nie zmienia stanu. |
| `potwierdz_obserwacje(page)` | Czy menu profilu mowi teraz, ze go OBSERWUJEMY. Otwiera menu i czyta. |
| `obserwuj_profil(handle, wyslij)` | Obserwuje cudzy profil — jego notki trafiaja do naszego kanalu. |
| `kogo_polecamy(page)` | Kogo nasza publikacja poleca — z API, nie z pamieci. |
| `polec_publikacje(fraza, powod, wyslij)` | Dodaje REKOMENDACJE publikacji. Domyslnie wypelnia i NIE zatwierdza. |
| `zasubskrybuj(handle, wyslij)` | Subskrybuje cudzy profil. Ląduje w skrzynce właściciela, więc wąsko. |
| `_esc(t)` *(wewn.)* | — |
| `rozbierz_artykul(sciezka)` | Rozkłada plik artykułu na tytuł, podtytuł i treść jako HTML. |
| `wypelnij_artykul(page, artykul, obraz)` | Wkłada tytuł, podtytuł, grafikę i treść do otwartego edytora. |
| `wstaw_przycisk_subskrypcji(page)` | Jeden przycisk subskrypcji, po ostatnim akapicie a przed źródłami. |
| `tresc_oswiadczenia()` | Oświadczenie „Jak to robię" — z pliku, nie z drugiej kopii w kodzie. |
| `ustaw_oswiadczenie_ai(wyslij)` | Ustawia stałe oświadczenie pokazywane każdemu, kto skanuje nas pod kątem AI. |
| `wystaw_odpowiedz_pod_artykulem(url_artykulu, autor, tekst, wyslij)` | Odpowiada pod KONKRETNYM komentarzem pod naszym artykułem. |
| `potwierdz_artykul(page, tytul)` | Pyta Substacka, czy artykuł naprawdę jest opublikowany. |
| `wystaw_artykul(sciezka_md, sciezka_png, wyslij)` | Wystawia artykuł na Substacku. Domyślnie WYPEŁNIA i NIE WYSYŁA. |
| `_watek_z_paginacja(page, nid, stron)` *(wewn.)* | Caly watek notki — ze WSZYSTKICH stron, nie tylko z pierwszej. |
| `potwierdz_odpowiedz(page, note_id, tekst)` | Pyta Substacka, czy nasza odpowiedź naprawdę jest w wątku — i KTORA. |
| `wystaw_odpowiedz(note_id, tekst, wyslij, kontekst, rodzaj)` | Odpowiada w watku — pod nasza notka albo w cudzej dyskusji. |
| `wystaw_notke(tekst, wyslij, typ, forma, model)` | Wystawia notkę. Domyślnie WYPEŁNIA i NIE WYSYŁA. |
| `zapamietaj_platny_host(host, prawo)` | Host, ktory wprost mowi, ze komentowac moga tylko placacy. |
| `hosty_tylko_dla_placacych()` | Hosty, gdzie komentowac moga tylko placacy — do odsiania PRZED ocena. |
| `zapomnij_platny_host(host)` | Udany komentarz kasuje host z listy — wydawca mogl zmienic ustawienia. |
| `hosty_gdzie_komentarz_nie_wchodzi(min_prob, dni)` | Hosty, gdzie w ostatnich `dni` dniach probowalismy >=2 razy i ANI RAZ |
| `mozna_komentowac(url)` | Czy pod tym tekstem wolno nam w ogóle napisać. |
| `uchwyt_publikacji(host)` | Nazwa konta do obserwowania — z hosta albo, gdy trzeba, z API. |
| `juz_sie_odezwalismy(page, url)` | Czy JUZ napisalismy cokolwiek pod tym postem albo pod ta notka. |
| `bez_znacznikow(html)` | Sam tekst, bez HTML-a. Do promptu notki promujacej szlo 9000 znakow |
| `potwierdz_adres_artykulu(page, tytul)` | Prawdziwy adres opublikowanego artykulu — od Substacka, nie z tytulu. |
| `potwierdz_komentarz(page, url, tekst)` | Pyta Substacka, czy komentarz naprawdę wisi — zamiast wierzyć kliknięciu. |
| `wystaw_komentarz(url, tekst, wyslij, kontekst)` | Wystawia komentarz pod cudzym postem. Domyślnie WYPEŁNIA i NIE WYSYŁA. |
| `read_pages(urls)` | Otwiera strony w przeglądarce i zwraca ich widoczny tekst. |
| `restackuj_w_kanale(ile, decyzja, wyslij)` | Podaje dalej cudze notki z wlasnym zdaniem. |
| `_notka_przy_przycisku(przycisk)` *(wewn.)* | Tresc i autor notki, przy ktorej stoi ten przycisk. |

### `llm.py` — JEDYNA warstwa dostępu do modeli i liczenia kosztu

823 wierszy, 15 funkcji na poziomie modułu, 3 klas

| funkcja | co robi |
|---|---|
| `_dostawca(model)` *(wewn.)* | Czyj to model. JEDNO miejsce, zeby nie rozjechalo sie z kontrola kluczy. |
| `_preflight(purpose, conn, run_id)` *(wewn.)* | Warunki, które decydują, czy wywołanie może się w ogóle udać. |
| `_narzedzie_wyszukiwania(model)` *(wewn.)* | Nazwa narzedzia wyszukiwania; ostrzega RAZ NA PROCES o braku wpisu. |
| `_cost(model, tokens_in, tokens_out, web_searches, cache_hit)` *(wewn.)* | — |
| `_log(purpose, model, tin, tout, searches, usd, verified)` *(wewn.)* | — |
| `_call_claude(purpose, system, user, web_search)` *(wewn.)* | — |
| `_call_deepseek_responses(purpose, system, user)` *(wewn.)* | DeepSeek przez /responses z server-side `web_search`. |
| `_deepseek_pick_from_urls(purpose, system, user, urls)` *(wewn.)* | Drugie, tanie wywołanie: wybierz z adresów, które wyszukiwanie już zwróciło. |
| `_call_deepseek(purpose, system, user)` *(wewn.)* | — |
| `przejsciowy(exc)` | Czy ten błąd ma szansę minąć sam. |
| `call(purpose, system, user)` | Woła model właściwy dla etapu i zapisuje koszt. Zwraca tekst odpowiedzi. |
| `obraz(opis)` | Generuje grafikę do artykułu i zapisuje jej koszt tam, gdzie resztę. |
| `_obiekty_json(tekst)` *(wewn.)* | Kolejne ZBILANSOWANE obiekty JSON w tekscie, od lewej. |
| `ratuj_json(purpose, tekst, ksztalt)` | Drugie podejście do odpowiedzi, która nie zawierała JSON-a. |
| `parse_json(text)` | Wyciąga obiekt JSON z odpowiedzi modelu. |

### `gates.py` — bramki jakości; żadna nie blokuje

535 wierszy, 18 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_digit_tokens(text)` *(wewn.)* | — |
| `_niepobrane(card)` *(wewn.)* | Twierdzenia oznaczone `not_fetched` — dolozone, nie wyciagniete. |
| `_korpus_pobranych(card)` *(wewn.)* | Liczby z materialu, ktory NAPRAWDE pobralismy. |
| `numbers_outside_corpus(body, card)` | Liczby w tekście, których nie ma nigdzie w POBRANYM materiale. |
| `deterministic_floors(body, card, poprzednie)` | Podłogi bez modelu: 0 USD, milisekundy, zero wywołań. |
| `_akapity(body)` *(wewn.)* | — |
| `zastrzezenia(body)` | Zastrzezenia w pierwszej osobie. Budzet: jedno na tekst. |
| `zakazane_otwarcie(body)` | Pierwsze zdanie, jesli kaze czytelnikowi isc cos obejrzec. |
| `statystyki_bez_zrodla(body)` | Zdania, ktore niosa liczbe i udaja, ze maja na nia zrodlo. |
| `niewiadome_na_koncu(body)` | Zbiorczy akapit o niewiadomych w ostatniej trzeciej tekstu. |
| `odcisk_formy(body)` | Zgrubny szkielet tekstu — do porownania z poprzednimi, nie do oceny. |
| `powtorzona_forma(body, poprzednie, prog)` | Czy ten tekst ma ksztalt ktoregos z poprzednich. |
| `uwagi_z_formy(obserwacja, body)` | Zamienia obserwacje modelu w uwagi. MODEL OBSERWUJE, KOD ROZSTRZYGA. |
| `pozycja_w_tekscie(cytat, body)` | Gdzie w tekście stoi ten cytat, jako ułamek długości. Informacja, nie ocena. |
| `szerokosc_podstawy(card)` | Na ilu ODREBNYCH serwisach stoja potwierdzone twierdzenia. |
| `frazy_z_instrukcji(body, dlugosc)` | Czy pisarz wklein do tekstu wlasne polecenie. |
| `verdict(findings)` | Artykuł powstaje ZAWSZE. Decyzja właściciela z 2026-08-15. |
| `zapowiedziany_akapit_granic(body)` | Czy akapit o granicach zaczyna sie od zdania o samym sobie. |

### `db.py` — schemat i zapis

333 wierszy, 11 funkcji na poziomie modułu, 1 klas

| funkcja | co robi |
|---|---|
| `kanal(nazwa)` | Na czas bloku kazde zapisane wywolanie dostaje `akcja = nazwa`. |
| `now()` | — |
| `_odmow_produkcji(db_path)` *(wewn.)* | GLOSNA odmowa: wyjatek, nie ciche pominiecie. |
| `connect(path)` | Otwiera bazę i zakłada schemat, jeśli go nie ma. |
| `_dopisz_brakujace_kolumny(conn)` *(wewn.)* | — |
| `start_run(conn, stage, tryb)` | Nowy przebieg. `tryb` to „produkcja" albo „test". |
| `tryb_przebiegu(conn, run_id)` | Tor, do ktorego nalezy przebieg. Bez przebiegu — produkcja. |
| `finish_run(conn, run_id, status, stage, note)` | — |
| `record_call(conn, **fields)` | Zapisuje wywołanie, wstawiając TYLKO te kolumny, które ktoś podał. |
| `spent_usd(conn, since_prefix, tryb)` | Suma kosztów od znacznika czasu zaczynającego się danym prefiksem. |
| `recent_domains(conn, limit)` | Domeny z ostatnich N artykułów — wejście do reguły różnorodności. |

### `jezyki.py` — wzorce bramek zalezne od jezyka; przy jezyku bez wzorcow bramka jest JAWNIE wylaczona zamiast cicho nic nie lapac

257 wierszy, 5 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_ostrzez(jezyk, czego_brak)` *(wewn.)* | Raz na proces, ale GLOSNO. Cicha bramka jest gorsza od jej braku. |
| `wzorzec(nazwa, jezyk)` | Skompilowany wzorzec bramki dla tego jezyka. Brak = jawnie wylaczona. |
| `frazy(nazwa, jezyk)` | Lista fraz dla tego jezyka. Brak = pusta lista i glosne ostrzezenie. |
| `znane_jezyki()` | — |
| `brakujace(jezyk)` | Czego brakuje temu jezykowi wobec angielskiego. Pusta lista = komplet. |

### `konfiguracja.py` — wczytanie `konfiguracja.toml` — jeden plik zamiast edycji w kilkudziesieciu miejscach; nie podejmuje decyzji, tylko podaje wartosci do `config.py`

311 wierszy, 12 funkcji na poziomie modułu, 1 klas

| funkcja | co robi |
|---|---|
| `_napis(v, gdzie)` *(wewn.)* | — |
| `_data_albo_pusto(v, gdzie)` *(wewn.)* | Dzien w postaci RRRR-MM-DD albo pusty napis znaczacy „nigdy". |
| `_liczba(v, gdzie)` *(wewn.)* | — |
| `_prawda(v, gdzie)` *(wewn.)* | — |
| `_lista_napisow(v, gdzie)` *(wewn.)* | — |
| `_lista_napisow_moze_pusta(v, gdzie)` *(wewn.)* | Lista napisow, w ktorej PUSTA jest poprawna odpowiedzia. |
| `_widelki(v, gdzie)` *(wewn.)* | Zakres [od, do]. Wolumeny sa losowane z widelek, nie stale. |
| `_slownik_list(v, gdzie)` *(wewn.)* | Tablica `klucz = [napisy]`. Pusta lista jest DOZWOLONA i coś znaczy. |
| `_slownik_napisow(v, gdzie)` *(wewn.)* | — |
| `sciezka(agent_dir)` | — |
| `wczytaj(plik)` | Surowa zawartosc pliku, sprawdzona co do ksztaltu. Brak pliku = pusto. |
| `zastosuj(dane, cfg)` | Wklada wartosci do modulu `config`. Oddaje liste tego, co przestawiono. |

### `kanal.py` — pamięć o cudzych publikacjach

295 wierszy, 10 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_historia()` *(wewn.)* | — |
| `zapamietaj_komentarz(post)` | Odnotowuje, u kogo dzis komentowalismy. |
| `klucz_publikacji(post)` | Kim jest autor posta. Z ADRESU, bo nazwa publikacji bywa pusta w kanale. |
| `_wiek_minut(data)` *(wewn.)* | — |
| `_za_swiezy(post, widelki)` *(wewn.)* | Czy post jest na tyle swiezy, ze komentarz wygladalby jak czujka bota. |
| `wartosc_celu(x)` | Klucz sortowania celow: WCZESNIE przed GLOSNO. |
| `_za_niedawno_u_nich(post)` *(wewn.)* | Czy komentowalismy u tej publikacji w ostatnich dniach. |
| `posty_z_kanalu(ile)` | Ostatnie posty z kanalu czytelnika, z liczba komentarzy i reakcji. |
| `notki_z_kanalu(ile)` | Cudze notki, pod ktorymi mozna wejsc w dyskusje. |
| `szukaj_nowych(ile)` | Szuka NOWYCH kont wyszukiwarka Substacka, poza naszym kregiem. |

### `alarm.py` — kontrola sesji, zdrowia i alarm do właściciela

983 wierszy, 23 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_ustawienia()` *(wewn.)* | — |
| `skonfigurowany()` | — |
| `_ostatnio(klucz)` *(wewn.)* | — |
| `_zapisz(klucz)` *(wewn.)* | — |
| `wyslij(klucz, temat, tresc)` | Wysyła alarm. `klucz` identyfikuje RODZAJ problemu, nie pojedynczy wypadek. |
| `artykul_zalegly()` | Czy gotowy artykul lezy na dysku niewystawiony dluzej niz dobe. |
| `sprawdz_sesje_i_ostrzez()` | Pilnuje jedynej rzeczy, która zatrzymuje agenta bez żadnego błędu. |
| `sprawdz_przebiegi_i_ostrzez(ile)` | Alarmuje, gdy agent pada raz za razem. |
| `_polaczenie()` *(wewn.)* | — |
| `cisza()` | Czy agent w ogole cos ostatnio zrobil. |
| `zawieszone()` | Przebiegi, ktore zostaly w stanie RUNNING na zawsze. |
| `dysk()` | — |
| `nadaktywnosc()` | Czy agent nie zapetlil sie i nie zasypuje Substacka. |
| `koszt()` | Czy zblizamy sie do sufitu — dziennego ALBO miesiecznego. |
| `wolumeny()` | Czy agent robi tyle, ile deklaruje — czy tylko wyglada, ze robi. |
| `powtorki()` | Czy agent nie zaczal pisac wciaz tego samego. |
| `kopia_subskrybentow()` | Czy istnieje AKTUALNA kopia listy subskrybentow. |
| `pomiar_wzajemnosci()` | Czy nadal mamy z czego liczyc, kto sie odwzajemnia. |
| `wydarzenie_bez_pokrycia()` | Wydarzenie odhaczone jako obsluzone, a w tresci ani slowa o nim. |
| `bank_bez_tematow()` | Czy w banku zostalo dosc ROZNYCH tematow na dzisiejsze notki. |
| `sprawdz_wszystko()` | Uruchamia komplet kontroli i alarmuje o tym, co znalazl. |
| `przeglad(dni)` | Co agent NAPRAWDE zrobil przez ostatnie dni i gdzie sie pomylil. |
| `_co_z_tego_wyszlo(wpisy)` *(wewn.)* | Czy nasze dzialania w ogole wracaja — i ktore z nich. |

### `style.py` — korpus stylu dla pisarza

198 wierszy, 9 funkcji na poziomie modułu, 1 klas

| funkcja | co robi |
|---|---|
| `_plik_przypiec()` *(wewn.)* | — |
| `_sha256(text)` *(wewn.)* | — |
| `split_paragraphs(raw)` | Deterministyczny podział na akapity; styl końca linii nie zmienia numeracji. |
| `bajty_kanoniczne(raw)` | Bajty korpusu niezależne od tego, jak git zmaterializował plik. |
| `wczytaj_przypiecia()` | Przypięcia korpusu z pliku obok niego. Brak pliku = czytelny błąd. |
| `load_examples()` | Zwraca zatwierdzone fragmenty stylu albo rzuca, jeśli korpus się nie zgadza. |
| `load_profiles()` | Profil pozytywny i negatywny stylu artykułu. |
| `_z_marka(tekst)` *(wewn.)* | Podstawia `{marka}` w profilu stylu. Profil bez pola zostaje bez zmian. |
| `corpus_words()` | Wszystkie słowa korpusu — podłoga porównuje tekst z korpusem, nie z alfabetem. |

### `kopia_subskrybentow.py` — kopia jedynego aktywa, którego nie da się odtworzyć

203 wierszy, 4 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_wierszy(tekst)` *(wewn.)* | — |
| `_to_lista_subskrybentow(tekst)` *(wewn.)* | Czy to naprawde eksport listy, a nie przypadkowy plik albo strona HTML. |
| `pobierz_z_panelu()` | Sciaga liste z wlasnego panelu i zapisuje ja jako CSV do `przychodzace/`. |
| `main()` | — |

### `config.py` — wszystkie liczby i decyzje w jednym miejscu (patrz ZAŁĄCZNIK B)

2922 wierszy, 27 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_korpus_stylu()` *(wewn.)* | — |
| `_env(name, default)` *(wewn.)* | — |
| `stawka_deepseek(model, kiedy)` | Stawka DeepSeeka z uwzglednieniem pory doby po wejsciu nowej taryfy. |
| `pora_na_publikacje(kiedy)` | Czy teraz wolno wystawiac NOTKI — wg zegara CZYTELNIKOW, nie serwera. |
| `w_szczycie(kiedy)` | Czy teraz obowiazuje droga taryfa. |
| `narzedzie_wyszukiwania(model)` | Nazwa narzedzia wyszukiwania i ewentualne ostrzezenie. |
| `sufit_dnia(dzien)` | Sufit obowiazujacy W TYM DNIU, nie dzisiaj. |
| `kotwica_dlugosci(glebokosc)` | Zdanie kalibrujace dlugosc, dobrane do ilosci materialu. |
| `dlugosc_dla(glebokosc)` | Ile slow ma miec artykul o tej glebokosci. |
| `_tokens_for(chars)` *(wewn.)* | — |
| `losowa_postawa()` | Ktora postawa dla TEGO komentarza. Wagi, nie rownomiernie. |
| `losowe_otwarcie()` | — |
| `losowa_dlugosc()` | Ile slow ma miec ta konkretna wypowiedz. |
| `losowy_ksztalt_mysli()` | Ktory ksztalt dostaje ta MYSL. Losowany, bo wybor zbiega do stalej. |
| `normy_dzienne()` | Ile czego POWINNO wychodzic dziennie — srodek widelek. |
| `_cisza_z_hasza(dzien)` *(wewn.)* | — |
| `cichy_dzien(kiedy)` | Czy dzis nie nadajemy. Ta sama odpowiedz przez caly dzien. |
| `timeout_for(max_tokens)` | Termin w sekundach, który realnie pokrywa podany sufit tokenów. |
| `_w_darmowym_tescie()` *(wewn.)* | Czy uruchomiony program to test, ktory NIE MA prawa placic. |
| `pod_produkcyjnymi_danymi(sciezka)` | Czy ta sciezka lezy w PRAWDZIWYM katalogu danych (takze w podkatalogu). |
| `_moduly_projektu()` *(wewn.)* | Zaimportowane moduly z `agent-v2/`, bez samych testow. |
| `uzyj_katalogu_danych(katalog, utworz)` | Przestawia `DATA_DIR` I KOMPLET sciezek z niego policzonych. |
| `przywroc_katalog_danych(zdjecie)` | Cofa `uzyj_katalogu_danych`. Bez tego nastepny test dziedziczy podmiane. |
| `losowy_ruch_koncowy()` | Czym konczy sie TEN artykul. Rowne szanse, bez powtarzania formuly. |
| `losowa_liczba_paraleli(glebokosc)` | Ile paraleli w drugim akcie. Krotki artykul nigdy nie bierze trzech. |
| `losowe_generatory(ile)` | Ktore wzorce w tym przebiegu. Ten sam generator dwa dni z rzedu daje |
| `co_teraz_w_reku(kiedy)` | Rzeczy, ktorych czytelnik dotyka wlasnie teraz. |

### `statystyki.py` — co przyniosła każda pozycja: wejścia, reakcje, subskrypcje

519 wierszy, 10 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_liczba(x)` *(wewn.)* | Cokolwiek z API -> int. Nigdy nie rzuca. |
| `_karty(dane)` *(wewn.)* | `cards` -> {cardId: karta}. Odporne na `cards` = None i wpisy bez id. |
| `_pozycje(karta)` *(wewn.)* | `items` listCarda -> {tytul: liczba}, w kolejnosci z API. |
| `_suma(karta)` *(wewn.)* | Liczba zbiorcza z karty: `value`, `count`, `total`, naglowek, suma pozycji. |
| `z_kart(dane)` | Odpowiedz `/api/v1/note_stats/c-{ID}` -> plaski rekord o stalych kluczach. |
| `_plik()` *(wewn.)* | Sciezka liczona przy KAZDYM wywolaniu, nie raz przy imporcie. |
| `zapisz(rodzaj, identyfikator, rekord, tekst)` | Dopisuje JEDEN pomiar. Nigdy nie przerywa dzialania agenta. |
| `wczytaj(rodzaj)` | Wszystkie pomiary z pliku, w kolejnosci zapisu. Uszkodzone linie pomija. |
| `najnowsze_per_pozycja(rodzaj)` | {identyfikator: ostatni pomiar}. To sie czyta przy raporcie. |
| `podsumowanie(rodzaj)` | Sumy i srednie PO POZYCJACH, nie po pomiarach. |

### `bramki.py` — co może zatrzymać treść — wyliczone z drzewa składni, nie spisane z pamięci

258 wierszy, 7 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_zrodlo(nazwa)` *(wewn.)* | — |
| `_komentarz_nad(linie, nr, ile)` *(wewn.)* | Ostatnia linia komentarza nad wskazanym wierszem — zwykle uzasadnienie. |
| `_rodzic_funkcji(drzewo)` *(wewn.)* | Mapa: numer wiersza -> nazwa funkcji, w ktorej ten wiersz lezy. |
| `wstrzymania_publikacji(pelne)` | Kazde miejsce, ktore ustawia `safe_to_post` na falsz. |
| `warunki_przed_wystawieniem(pelne)` | Kazde wystawienie tresci i warunki, pod ktorymi stoi. |
| `przerwania_w_petlach()` | `continue` i `return` w petlach po kandydatach — czyli „ten odpada". |
| `raport(pelne)` | — |

### `raport_statystyk.py` — te same dane w tabeli dla człowieka

278 wierszy, 5 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_skrot(tekst, ile)` *(wewn.)* | — |
| `_mediana(liczby)` *(wewn.)* | — |
| `dwie_epoki(najnowsze)` | Epoka AI osobno, epoka ukrytych systemow osobno. |
| `wzrost_konta()` | Ilu nas czyta i czy tego przybywa. |
| `main()` | — |

### `korpus_kanalow.py` — o czym mówi się w tym tygodniu — zaczyn tematów, nigdy źródło

374 wierszy, 6 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `oczysc(tytul)` | Zdejmuje obietnice, zostawia zdarzenie. |
| `przetworz(wpisy)` | (nazwa_kanalu, element) -> kandydaci. Czysta funkcja, testowalna. |
| `_rdzen(temat)` *(wewn.)* | Slowa nosne tytulu — do porownywania, czy dwa kanaly mowia o tym samym. |
| `_numer_wersji(slowo)` *(wewn.)* | Czy token wyglada na numer wydania: ma cyfre i nie jest rokiem. |
| `wielkie_wydarzenia(korpus, min_kanalow, min_wspolnych, swiezosc_dni, min_kanalow_premiery)` | Rzeczy, o ktorych mowi NARAZ kilka roznych kanalow. |
| `korpus_kanalow(ile)` | — |

### `aktualne_modele.py` — jakie modele istnieją DZIŚ; pytane na żywo, nie z pamięci

186 wierszy, 4 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `_swieze(dane)` *(wewn.)* | Czy zapisana odpowiedz jest jeszcze wazna. |
| `wczytaj()` | Ostatnia zapisana odpowiedz. Pusty slownik, gdy nie ma albo jest zepsuta. |
| `pobierz(conn, run_id, wymus)` | Aktualny stan modeli. Z pliku, gdy swiezy; inaczej pyta na nowo. |
| `jako_tekst(dane)` | Stan modeli w postaci, ktora wchodzi do promptu. |

### `artykul_z_puli.py` — artykuł bierze temat z tej samej puli, co notki

1442 wierszy, 14 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `temat_z_faktu(conn, run_id, fakt)` | Zamienia udokumentowany fakt w brief artykulu. |
| `glebokosc_z_oceny(ocena)` | RICH / SINGLE / THIN — liczone z tego, co `warto_pisac` ZOBACZYLO. |
| `uniesie_artykul(brief)` | Czy z tego faktu da sie napisac TYSIAC SLOW, czy tylko dwa zdania. |
| `wybierz_fakt(conn, run_id, ile)` | Swiezy fakt z puli ciekawostek, ktory NIE powtarza zadnego artykulu. |
| `main()` | Otwiera przebieg, oddaje robote i ZAMYKA go — takze przy wyjatku. |
| `_zrob_miejsce_na_fakt(card)` *(wewn.)* | Robi miejsce na wstrzykniete twierdzenie, nie tracac zadnego ZRODLA. |
| `_rozszerz_najstarsze(card, data_faktu)` *(wewn.)* | Data wstrzyknietego zrodla wazy — ale TYLKO w strone ostrzezenia. |
| `_przebieg(conn, run_id)` *(wewn.)* | — |
| `_katalog_ratunku()` *(wewn.)* | Katalog OBOK `ARTICLES_DIR`, nigdy w nim. |
| `_opublikuj(sciezka)` *(wewn.)* | Wystawia gotowy artykul, probujac wiecej niz raz. NIE JEST BRAMKA. |
| `_ramka(powod, brak, katalog)` *(wewn.)* | Ostrzezenie, ktore idzie na POCZATEK `.md`, a nie tylko obok niego. |
| `_zrodla(card)` *(wewn.)* | Sekcja `## Sources` — bez pytania bazy o nazwy zrodel. |
| `_ratuj_tekst(run_id, brief, card, draft, etap, exc, raport)` *(wewn.)* | Gotowy tekst na dysk, gdy budzet albo wylacznik przerywa PO pisaniu. |
| `_napisz_i_zapisz(conn, run_id, brief, card)` *(wewn.)* | Od bramki „warto pisac" do zapisu i grafiki. |

### `norma.py` — licznik produkcji: ile agent wystawil wobec normy dziennej

1106 wierszy, 13 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `budzety_dzienne()` | Ile agent SOBIE ZALOZYL kazdego dnia — z pliku, nie z dzisiejszej konfiguracji. |
| `_data(dzien)` *(wewn.)* | „2026-08-30" -> datetime w UTC. `cichy_dzien` pyta o obiekt, nie napis. |
| `_poprawna_data(dzien)` *(wewn.)* | Czy da sie z tego zrobic date. Zepsuty wpis ma znikac, nie zabijac raport. |
| `wczytaj(dni)` | (zrobione, nieudane) — liczniki per dzien i rodzaj. |
| `slad_dziennika(zalozone)` | (najstarszy znany dzien, zbior dni z JAKIMKOLWIEK wpisem w dzienniku). |
| `_znak(ile, norma)` *(wewn.)* | Jak daleko od planu NA TEN DZIEN. Sam PROCENT jest ten sam, co w `alarm.py`. |
| `dni_okna(dni, z_wpisami, zalozone, najstarszy)` | Wszystkie dni okna — TAKZE te, w ktorych nie wyszlo NIC. |
| `_komorka(ile, cel, wyciszony, ma_wpisy, w_toku, szacowany)` *(wewn.)* | Jedna kratka tabeli. `cel is None` znaczy „planu nie znamy". |
| `przebiegow_dzis()` | Ile przebiegow agenta domknelo sie dzis. Zero, gdy bazy nie ma. |
| `godziny_przebiegow()` | Minuty od polnocy UTC, o ktorych systemd odpala agenta. |
| `przebiegow_naleznych(teraz)` | (ile przebiegow POWINNO juz oddac swoja czesc, ile ich jest na dobe). |
| `slad(dni)` | Gdzie dokladnie psuja sie publikacje — wg pozycji w serii i odstepu. |
| `main()` | — |

### `audyt_tematow.py` — audyt segmentu tematow na zywych danych: jedenascie etapow, od kanalow po zwrot do puli

326 wierszy, 4 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `etap(nr, nazwa)` | — |
| `werdykt(nazwa, stan, szczegol)` | — |
| `bank()` | Indeks kandydatow, albo pusto — narzedzie audytowe NIE MOZE sie wywalac. |
| `main()` | — |

### `audyt_researchu.py` — audyt segmentu researchu na zywych danych: dyskoveria, pobieranie, martwe hosty, karta dowodowa

196 wierszy, 3 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `etap(nr, nazwa)` | — |
| `werdykt(nazwa, stan, szczegol)` | — |
| `main()` | — |

### `audyt_systemu.py` — audyt CALEGO systemu na zywych danych: publikowanie, normy, komentarze, statystyki, artykul, pieniadze, pamiec

654 wierszy, 7 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `czy_pominiecie(rodzaj)` | Czy ten wpis jest pominieciem. Po KONCOWCE nazwy, nie po liscie nazw. |
| `policz_rodzaje(wpisy)` | (udane, nieudane, pominiete) — trzy liczniki, bo stany naprawde sa trzy. |
| `etap(nr, nazwa)` | — |
| `werdykt(nazwa, stan, szczegol)` | — |
| `dziennik()` | — |
| `dzien(w)` | — |
| `main()` | — |

### `wzajemnosc.py` — czy zaczepieni sie odwzajemniaja: liczy PO naszej akcji, osobno stan nieorzekalny

1418 wierszy, 25 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `wczytaj(nazwa)` | Wiersze pliku JSONL z katalogu danych. Uszkodzona linia nie kasuje reszty. |
| `_chwila(tekst)` *(wewn.)* | ISO-8601 na moment w UTC, bez strefy. Zwraca None zamiast rzucac. |
| `_nazwa(tekst)` *(wewn.)* | Nazwa wyswietlana do porownywania: male litery, jedna spacja. |
| `_uchwyt(tekst)` *(wewn.)* | Uchwyt do porownywania: male litery, same znaki alfanumeryczne. |
| `_licznik_z_chwili(kiedy, liczniki)` *(wewn.)* | Zapis `wzrost.jsonl` z tego samego momentu, co zrzut imienny — albo nic. |
| `zrzuty_czytelnikow()` | Zrzuty po kolei, KAZDY Z OCENA, CZY NIE JEST OKROJONY. |
| `czytelnicy()` | Uchwyt czytelnika -> co o nim wiemy ze zrzutow. |
| `kolejnosc(wpis, akcja)` | Czy czytelnik pojawil sie PO naszym dzialaniu, PRZED nim, czy nie wiadomo. |
| `okno_pomiaru()` | Od kiedy do kiedy w ogole widzimy, kto nas czyta. |
| `pokrycie()` | Ilu czytelnikow LICZY Substack, a ilu umiemy nazwac po imieniu. |
| `_pusty_kubel()` *(wewn.)* | Swiezy komplet licznikow. Funkcja, a nie stala: `dict(STALA)` kopiuje |
| `zaczepienia()` | Kogo zaczepilismy — osobno udane, nieudane i POMINIETE. |
| `odwzajemnienie()` | Ilu z zaczepionych pojawilo sie POTEM na naszej liscie czytelnikow. |
| `slepe_okno()` | O ile nasze najstarsze zaczepienie wyprzedza pierwszy zrzut czytelnikow. |
| `_reakcje()` *(wewn.)* | Zdarzenia `skutek` rozdzielone na kubelki plus licznik typow nieznanych. |
| `skad_przyszli()` | Ilu naszych czytelnikow zetknelo sie wczesniej z nasza trescia. |
| `_nasze_pozycje()` *(wewn.)* | Identyfikator wystawionej tresci -> rodzaj i chwila wystawienia. |
| `kanal_reakcji(reakcja, pozycje)` | Ktorego NASZEGO kanalu dotknal czlowiek — z CELU reakcji, nie z jej typu. |
| `opoznienia()` | Dwa rozne czasy, celowo NIE zsumowane w jeden. |
| `kanaly()` | Co poprzedzilo pojawienie sie czytelnika — osobowo i pozycyjnie. |
| `pomiar_oslepl()` | Czy w ogole mamy z czego liczyc wzajemnosc. |
| `_procent(licznik, mianownik)` *(wewn.)* | — |
| `naglowek()` | Jeden wiersz bez zrzutow albo cztery do szesciu. Liczby z mianownikiem. |
| `raport()` | Pelna odpowiedz na cztery pytania. Kazda liczba z mianownikiem. |
| `main()` | — |

### `migracja_okno_promocji.py` — jednorazowo: data publikacji z dziennika do kolejki promocji

97 wierszy, 2 funkcji na poziomie modułu, 0 klas

| funkcja | co robi |
|---|---|
| `daty_publikacji()` | Tytul artykulu -> data pierwszej udanej publikacji (YYYY-MM-DD). |
| `main()` | — |
