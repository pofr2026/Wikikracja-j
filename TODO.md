# OGÓLNE

- Do czatu: filtr tylko nieprzeczytane
- Do emaila powitalnego dodać https://lobbyobywatelskie.wikikracja.pl/board/view/25/
- Nowa osoba akceptuje zasady w momencie pierwszego logowania
- Dokończyć Fixtures i dodać je do skryptu instalacyjnego. Fixtures z przepisami, pokojami i ogłoszeniami. Start: (publiczna strona startowa dla niezalogowanych) i Footer: (publiczna stopka). Customowy email. Wszystkie te elementy dać do nowego działu.
- Backup kontaktów, przepisów, ogłoszeń, itd. Każdy powinien móc zrobić w postaci fixtures i md.

# ZADANIA (TASKS)

- Etykiety w Zadaniach. Tworzenie, przypisywanie i filtrowanie.
- Filtr, który pokazuje tylko moje zadania

# CHAT

## Błędy

- Po automatycznym usunięciu użytkownika chat rzuca błędami: `chat/models.py`, line 39, `displayed_name` — `AttributeError: 'NoneType' object has no attribute 'username'`
- Nie działa na Safari. ReferenceError: can't find variable TRANSLATION. Automate cross browser testing.

## Funkcjonalności

- Kolejne wiadomości od tej samej osoby: bez ramek
- Czaty pod ogłoszeniami?
- Każdy sam ustawia jak często chce otrzymywać wiadomości
- Szeregowanie wypowiedzi po ocenie
- Przypomnij wszystkim o danej wiadomości w danej dacie. Każdy może to włączyć.
- Wiadomość do wszystkich - chaty z najwyżej punktowanymi wypowiedziami
- Możliwość oznaczania wypowiedzi jako predykcji. Data przypomnienia albo wydarzenie po którym będzie można sprawdzić predykcję.
- Zmiana nazwy pokoju

# EMAILE

- Język w emailach ustawiony na sztywno - niezależnie od przeglądarki wysyłającego
- Funkcja wysyłająca emaile powtarza się 6 razy. Może moduł z multithreading? https://anymail.dev/en/v12.0/tips/django_templates/
- Opcja wyłączenia powiadomień email (Unsubscribe)
- Konfigurowalna częstotliwość wysyłania powiadomień o nowych zdarzeniach (czat, referenda, prośba o dołączenie)
- Lepsze wyjaśnienie do emaili z powiadomieniami (głosowania i czat oddzielnie)
- Emaile nie są tłumaczone na angielski
- Dodać tytuł propozycji w emailach (tytuł i treść)
- Dodać informację, że podanie emaila jest niezbędne żeby otrzymać hasło
- Dodać komunikat jeśli użytkownik odzyskuje hasło ale nie ma ustawionego emaila

# GŁOSOWANIA

## Błędy

- Jeśli czas trwania referendum jest ustawiony na 3 dni, to referendum w rzeczywistości trwa 4 dni

## Funkcjonalności

- Automatyczne głosowania Wiki. Poziom akceptacji, itd. https://www.kialo.com/ https://github.com/ehsanfakhraie/kialo/
- Głosowania stałe nad parametrami systemu (ile podpisów pod wnioskiem, czas trwania dyskusji, itd.)
- Szablony głosowań: sojusz z inną grupą, wymagana reputacja, czas trwania referendum, zrzutka, archiwizacja pokoi, wybory skarbnika, customowe
- Fixtures: przywrócić startowe referenda
- Dodać pole: ten przepis powinien być stosowany jeśli (czas, warunek)
- Podświetlanie guzików kiedy jest trwające referendum
- Pokazywać kto podpisał wniosek o referendum
- Zegarek odliczający czas do końca referendum
- Opis przy dodawaniu nowego przepisu: Co się dzieje; Jaki jest mechanizm; Jak to zmienić; Jakie będą konsekwencje
- Wersjonowanie Przepisów

# BOOKKEEPING

- Mechanizm do opłacania składki
- Umowy - ja pożyczam tobie, ja przechowuję tobie.
- Między sobą: kto, komu, ile, kiedy, za co. Squash: jeśli A wisi B, B wisi C, C wisi A 100zł to wszystko się zeruje. Rozliczenia gotówkowe / Śledzenie przekazywania przedmiotów
- Okresowe składki. Opłaty roczne, miesięczne, jednorazowe
- Wysyłanie okresowych emaili z przypomnieniami o płatnościach
- Oprogramować powiadomienia o składce

## Transakcje

- Zobowiązania powinny pojawiać się na koncie przed czasem i w tym momencie powinien być wysyłany email
- Kto wprowadza transakcję, kto stwierdza że kasa wpłynęła, a kto podpisuje?
- Zwykłe płatności grupy: transakcje wprowadza księgowy, ktoś inny potwierdza wpływ kasy.
- Księgowość i magazyn:
  - Filtr na transakcje
  - Okresowy import Członków do Klientów
  - Tworzenie przyszłych transakcji
  - Wysyłanie emaila z rachunkiem
  - Potwierdzanie otrzymania przedmiotu

## Stan kont / Raporty

- Składka powinna być widoczna na koncie grupy
- Podpisywanie kontraktu jeśli obie strony są w grupie
- Podpisywanie kontraktu jeśli grupa coś kupuje (zatwierdzanie wydatku)
- Odnotowywać kto dodał, zmienił i skasował wpis

## Umowy pomiędzy użytkownikami

- Potwierdzenie zwykłych płatności leży w sprzeczności z umowami. W umowach to druga strona potwierdza, że kasa wpłynęła.
- Chyba, że umowę/transakcję wpisze ta strona, która otrzymuje płatność

## Przedmioty / usługi / płatności

Do oddania / na sprzedaż / do wypożyczenia:
- Cena, jednostka (sztuka, dzień)
- Opis, komentarze, pliki, zdjęcia, filmy
- Ogłoszenia komercyjne (płatne) / prywatne i "oddam" (tańsze) / grupowe (ze wspólnej kasy)
- Tagi lub kategorie
- W użyciu od-do / wolne od-do / rezerwacja od-do
- Włączone / wyłączone
- Fungible / non-fungible
- Transakcje credit / debit

## Okresowe kredytowanie i debetowanie

- Miejsce użytkowania / dostępności
- Właściciel (jedna osoba, wielu, wszyscy)
- Potwierdzanie własności/użytkowania przez obie strony (podczas przekazywania)
- Obecny użytkownik ← naliczanie opłaty za czas użytkowania
- Parametry oferty/potrzeby: ilość, cena za sztukę, miejsce, cena za wynajem

# OGŁOSZENIA / BOARD

- Start i Footer powinny być opcjami podczas edycji ogłoszenia
- Dodać komentarze pod artykułami (albo czat room)
- Powiadomienia email przy zmianie treści artykułu (tylko przy okazji innych wiadomości)
- Edytowanie ogłoszeń tylko przez autora
- Zmiana autora jeśli ktoś zostanie wyrzucony z grupy
- Ocenianie artykułów. Najniżej oceniane trafiają do ukrytego archiwum.
- Wersjonowanie Ogłoszeń
- Przewijanie artykułów na blogu

# OBYWATELE

- Walidacja czyści formularz jeśli pierwsze pole jest nieprawidłowe (przy zapraszaniu nowej osoby)
- Dodaj opcję kasowania własnego konta i wszystkich danych użytkownika. Powinna być możliwość samodzielnego usunięcia z grupy ale też powinien być okres karencji po którym potwierdza się chęć odejścia. W okresie karencji będziemy mieli szansę zapytać co jest nie tak.
- Temat grace period (okres karencji) pojawił się też przy normalnym usuwaniu użytkowników oraz przy czasowej banicji (jako konsekwencji złamania przepisu). Może da się upiec 3 pieczenie przy jednym ogniu.
- Podczas zakładania konta powinny się wyświetlić aktualne zasady i trzeba je zaakceptować
- Okres próbny: wszystkie głosowania są zablokowane, finanse i emaile do ludzi nie są widoczne

- Banowanie użytkowników na określony czas. Stany usera: zbanowany czasowo, zbanowany na stałe, członek honorowy bez prawa głosu (obserwator)
- Ochrona czasowa. Banowanie poprzedzić możliwością rozmowy z osobą
- Ograniczenie praw osobom, które mają być wyrzucone
- Tłumaczenie nie działa: `templates/allauth/account/messages/email_confirmation_sent.txt`
- Próg akceptacji (chwilowy i przegłosowany)
- Dodawanie prywatnych notatek do osoby
- Potwierdzenie konta za pomocą SMSa
- Dodać losowanie osoby sprawującej daną funkcję
- Zmianę emaila, nazwiska i użytkownika przenieść do jednego formularza
- Możliwość dodawania własnych pól w Zasobach
- Link "obywatele" zmienić na "ludzie"
- Akceptacja/odrzucenie bez wchodzenia w profil osoby: https://www.reddit.com/r/django/comments/b3ow2b/_/

# HOME

- Imię, nazwisko, username from email, miasto
- Zgoda na warunki przed przystąpieniem do grupy (grupa jawna/tajna do custom_settings)
- GROUP_IS_PUBLIC oprogramować
- Formularz zapisywania się nie zapisuje danych
- Fixtures: Start i Footer do startowych fixtures
- Zrób obrazek po polsku pokazujący kolejne kroki zapisywania się do grupy
- "Ostatnie logowanie" nie działa jeśli ktoś się nie wylogował. Powinno być ostatnie kliknięcie.

# LIBRARY

- Dodać ocenianie książek (rating stars + recenzja/opis)
- Autor i tytuł zamiast obrazka zastępczego
- Tagi
- Wiki: assets - załączanie dowolnej ilości plików + galeria + okładka + autor + gatunek + czas wygasania + player audio/wideo + kto obecnie przechowuje (potwierdzenie od nadawcy i odbiorcy)

# ROLE I UPRAWNIENIA

- Legislator: opis kompetencji
- Administrator: superuser + opis kompetencji, konfiguracja systemu wedle wytycznych
- Sędzia: read only + opis kompetencji, weryfikacja czy przepisy są realizowane
- Senator: tworzenie przepisów, we współpracy z administratorem i sędzią
- Skarbnik: trzyma kasę i magazyn (potrzebna rola przed płatnościami)
- Prawa nadawane po wyborach
- Wyłączyć edycję przepisów przez administratora
- Doprowadzić do tego żeby superuser był zbędny (eliminacja tego co jest w After installation)
- Pozbyć się linka admin

# BEZPIECZEŃSTWO

- settings.SECURE_SSL_HOST
- Secure Cookies - rozdział security z 2 scoops
- https://docs.djangoproject.com/en/dev/ref/clickjacking/ → https://www.ponycheckup.com/result/
- fail2ban
- Czy można z powrotem włączyć apparmor? (proxy, wiki, jitsi)
- Włączyć FireWall na wszystkich domowych maszynach
- Powiadomienie o nowym logowaniu (np. z nowego urządzenia)
- Wyświetlać końcówkę adresu IP z którego loguje się użytkownik

# UI / UX

- Na komórce nie widać kto jest obecny (pogrubienie)
- Light and Dark mode https://youtu.be/n3lcjY4Mm00
- Burger menu na dół i sticky
- Tłumaczenie: "No file chosen" / "Choose File" https://stackoverflow.com/questions/14340519/html-input-file-how-to-translate-choose-file-and-no-file-chosen
- PiotrCOHOTO może pomóc z wyglądem
- Dodać opis Wikikracji wszędzie gdzie się da. Uwzględnić emocje i błędy poznawcze.
- Formularz kontaktowy - napisz do grupy

# KOMUNIKACJA

- Ludzie piszą do grupy. Grupy piszą do siebie.
- Wyślij wiadomość do całej grupy
- Kalendarz. Powiadomienia WhatsApp o spotkaniu
- signal-cli do wysyłania wiadomości
- Powiadomienia i głosowania SMS
- Django-WebRtc
- Automatyczny newsletter. Moduł do zapisywania ważnych wydarzeń i wysyłania zbiorczej informacji raz na tydzień.
- Okresowy automatyczny export wyników głosowań oraz listy użytkowników + wysyłka na email

# KONFEDERACJA (MULTI-GROUP)

- Mapa ze społecznościami. Zlinkować otwarte grupy.
- Nie można należeć do dwóch geograficznych grup ale może istnieć więcej niż jedna grupa dla danego obszaru.
- django-organizations https://django-organizations.readthedocs.io/en/latest/usage.html
- Zrobić SaaS: https://github.com/tomturner/django-tenants
- Grupy do skontaktowania się:
  - Śląski Związek Pszczelarzy (Zbigniew Bińko)
  - Ruch Autonomii Śląska

# INNE

- Oferuje/potrzebuje do oddzielnej tabelki ← wiele do wielu → Obywatel
- Firma do oddzielnej tabelki ← wiele do wielu → Obywatel
- Generowanie userów na podstawie listy mieszkańców/emaili/numerów mieszkań. Kod zapraszający z konta osoby zapraszającej. https://django-registration.readthedocs.io/en/3.1.1/
- Przy zakładaniu konta dla grupy podaj zakres adresów np. Wrzeciono 57A / 1-30
- Pre-definiowane głosowania
- Refactoring - przetłumaczyć zmienne na angielski
- Przenieść scripts do oddzielnego repo
- Zastępowanie zmiennych wartościami: `envsubst < config.txt > confidential_config.txt`
- PWA: https://web.dev/what-are-pwas/ https://beeware.org/
- Do woli: system reputacji oparty na predykcjach - kto trafniej przewiduje przyszłe wydarzenia zyskuje punkty, przyznanie się do błędu zatrzymuje utratę punktów.
- Zalogowanie się w systemie oznacza zgodę na warunki. Będąc członkiem grupy masz wpływ na przepisy w takim samym stopniu jak każdy inny obywatel.
- Podpowiedzi z możliwymi przepisami i biznesami do zrobienia
- Przykład sukcesu: https://wiadomosci.gazeta.pl/wiadomosci/7,114881,26810291,legalna-aborcja-w-argentynie-dzialaczki-kosciol-wiedzial.amp
- Do formularza wstępnego: Czy jesteś zwolennikiem DB? Czy zgadzasz się na przestrzeganie naszych zasad?

------------------------------------------------------------

# NIE BĘDZIE ZROBIONE

- Flutter - aplikacja na Androida i iOS
- Riot/Matrix integration - trzeba by tworzyć oddzielne konta na Riot dla użytkowników
- Pogrubić login w emailu - to jest w module venv
- Nasz człowiek w parlamencie
- Ankiety do błahych decyzji - zamiast tego up_vote/down_vote do chatu

------------------------------------------------------------

# ZROBIONE

- Dobrowolny formularz dla nowej osoby, która sama się zapisuje. Pola: dlaczego chcesz należeć do grupy, imię, nazwisko, telefon, miasto, zawód, hobby, biznes, umiejętności, wiedza.
- Zadania - małe guziczki za/przeciw w widoku listy.
- Jeśli ktoś próbuje zapisać się po raz drugi (ten sam email) to dostaje informację, że kandydatura jest w kolejce.
- Do Start dodano Zadania w realizacji i nowe wiadomości na czacie
- Chat: Treść u góry, wszystkie inne elementy wiadomości u dołu.
- Chat: room dla Task i Vote znika za szybko - częściowo zrobione ale nie są zachowywane na wieki
- Chat: Archiwum czatów powinno być pod guzikiem, nie pod rozwijaną listą. Bardziej ukryte żeby nie zaśmiecać interfejsu.
- Chat: Po utworzeniu propozycji - utworzyć dla niej pokój
- Chat: Linki do poszczególnych pokoi i wiadomości
- Chat: Po kliknięciu "Kliknij tutaj aby włączyć powiadomienia" — informacja, że trzeba zrestartować stronę.
- Chat: Pole tekstowe rośnie dynamicznie
- Chat: Przenieść wszystko z home do chat
- Głosowania: 2 dni przerwy pomiędzy końcem zbierania podpisów a możliwością wycofania podpisu
- Głosowania: Imienne dodawanie argumentów za i przeciw
- Głosowania: Pozytywy, negatywy referendum - każdy może komentować oba?
- Bookkeeping: Raporty używają "lazy loading" i przez to nie odświeżają się
- Bookkeeping: Kasowanie/edycja wpisów tylko przez autora
