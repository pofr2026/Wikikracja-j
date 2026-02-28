# PILNE
- Dodać opcję wyłączania powiadomień email (Unsubscribe)
- Osoby, które głosują Za zadaniem mogą zostać poproszone o pomoc
- Dodać opcję likwidacji własnego konta
- Wersjonowanie Ogłoszeń i Przepisów. Wydaje się, że to skomplikuje kod.

- backup kontaktów, przepisów, ogłoszeń, itd. Każdy powinien móc zrobić w postaci fixtures i md.
- okres próbny: wszystkie głosowania są zablokowane, finanse i emaile do ludzi nie są widoczne
- Powinna być możliwość samodzielnego usunięcie z grupy ale też powinien być okres karencji po którym potwierdza się chęć odejścia. W okresie karencji będziemy mieli szansę zapytać co jest nie tak.
- Temat grace period (okres karencji) pojawił się też przy normalnym usuwaniu użytkowników oraz przy czasowej banicji (jako konsekwencji złamania przepisu). Może da się upiec 3 pieczenie przy jednym ogniu.

- Kalendarz. Powiadomienia whatsapp o spotkaniu
- Dokończyć Fixtures i dodać je do skryptu instalacyjnego. Fixtures z przepisami, pokojami i ogłoszeniami. Start: (To jest publiczna strona startowa dostępna dla osób niezalogowanych) i Footer: (To jest publiczna stopka twojej strony).
- Jeśli czas trwania referendum jest ustawiony na 3 dni, to referendum w rzeczywistości trwa 4 dni
- Automatyczne głosowania Wiki. Poziom akceptacji, itd
- https://www.kialo.com/ https://github.com/ehsanfakhraie/kialo/
- Lepsze wyjaśnienie do emaili z powiadomieniami (głosowania i czat oddzielnie).
- Warto było ustawić "Tryb powolny" na wysoką wartość tak aby wysyłanie wiadomości na "Ważne Ogłoszenia" można było robić bardzo rzadko.
- Walidacja czyści formularz jeśli pierwsze pole jest nieprawidłowe (przy zapraszaniu nowej osoby)

# BOOKKEEPING
- mechanizm do opłacania składki
- Raporty używają "lazy loading" i przez to nie odświeżają się
- Kasowanie/edycja wpisów tylko przez autora
- Umowy - ja pożyczam tobie, ja przechowuję tobie.
- Między sobą: kto, komu, ile, kiedy, za co. Squash: jeśli A wisi B, B wisi C, C wisi A 100zł to wszystko się zeruje. Drobne pożyczki wzajemnie wraz z rozliczaniem abc. Funkcjonalność zliczania ile kto komu przekazał pieniędzy w danym roku. do 1000 a w jednym roku. Rozliczenia gotówkowe (kumulowanie płatności) / Śledzenie przekazywania przedmiotów
- Okresowe składki. Opłaty roczne, miesięczne, jednorazowe
- Wysyłanie okresowych emaili z przypomnieniami o płatnościach - również do customowej listy odbiorców

## TRANSAKCJE
- Zobowiązania powinny pojawiać się na koncie przed czasem i w tym momencie powinien być wysyłany email

## STAN KONT / RAPORTY
- Składka powinna być widoczna na koncie grupy
- Podpisywanie kontraktu jeśli obie strony są w grupie
- Podpisywanie kontraktu jeśli grupa coś kupuje (zatwierdzanie wydatku)
- odnotowywać kto dodał, zmienił i skasował wpis?
- księgowość i magazyn
  - filtr na transakcje
  - okresowy import Członków do Klientów
  - tworzenie przyszłych transakcji
  - wysyłanie emaila z rachunkiem
  - potwierdzanie otrzymania przedmiotu
- Kto wprowadza transakcję, kto stwierdza że kasa wpłynęła, a kto podpisuje?
- Zwykłe płatności grupy: Najczęściej transakcje wprowadza księgowy, ktoś inny powinien potwierdzić, że kasa wpłynęła.

## Umowy pomiędzy użytkownikami
- Potwierdzenie zwykłych płatności leży w sprzeczności z umowami. W umowach to druga strona potwierdza, że kasa wpłynęła.
- Chyba, że umowę/tranakcję wpisze ta strona, która otrzymuje płatność

## PRZEDMIOTY: przedmioty / usługi / płatności - do oddania / na sprzedaż / do wypożyczenia. FUNKCJONALNOŚCI:
 cena
- jednostka (sztuka, dzień)
- opis, komentarze, pliki, zdjęć, filmy
- ogłoszenia komercyjne są dużo płatne / ogłoszenia prywatne i "oddam" mniej płatne / grupowe są płatne ze wspólnej kasy.
- tagi lub kategorie
- w użyciu od do / wolne od do
- rezerwacja od do
- włączone / wyłączone
? fungible / none fungible - dotyczy pieniędzy, ale też porównywalnych usług (prąd) i wymienialnych przedmiotów
- transakcje typu credit / debit

## Okresowe kredytowanie i debetowanie
- obecnie miejsce użytkowania (geograficzne, raczej nie osoba) albo miejsce gdzie rzecz jest dostępna
- właściciel (jedna osoba albo wszyscy, może wielu właścicieli?)
- potwierdzanie własności/użytkowania przez obie strony (podczas przekazywania)
- obecny użytkownik <- naliczanie opłaty za czas użytkowania
- parametry oferty/potrzeby - ile dostępne, cena za sztukę, miejsce przechowywania, cena za wynajem.

# CHAT
- error ROOM_INVALID - Console > Application > Local Storage > lastUsedRoomID. Przy restarcie skasować wartość w lastUsedRoomID. Powinien być użyty najniższy isteniejący numer pokoju.
- Po automatycznym usunięciu użytkownika chat rzuca błędami:
  File "./chat/models.py", line 39, in displayed_name
  return self.get_other(user).username
  AttributeError: 'NoneType' object has no attribute 'username
- Więcej informacji w logach przy otwieraniu czatu. Szczególnie brakuje informacji które rekordy w bazie nie istnieją.
- Zwijanie Archiwum na czacie
- Po utworzeniu propozycji - utworzyć dla niej pokój
- Po kliknięciu "Kliknij tutaj aby włączyć powiadomienia" powinna być informacja, że trzeba zrestartować stronę.
- Linki do poszczególnych pokoi i wiadomości  
- Każdy sam ustawia jak często chce otrzymywać wiadomości
- przenieść wszystko z home do chat
- Tryb powolny nie powinien liczyć czasu od własnej ostatniej wypowiedzi ale od wypowiedzi ostatniej osoby.
- szeregowanie wypowiedzi po ocenie
- nie da się robić nowej linijki
- Przypomnij wszystkim o danej wiadomości w danej dacie. Każdy może to włączyć.
- Zabrać wszystkie niepotrzebne czynności z chat(request):
- Wiadomość do wszystkich - chaty z najwyżej punktowanymi wypowiedziami
- W dyżych grupach (cała Polska) nie powinno być opcji wyrzucania z grupy. Zamiast tego powinno być tylko wyrzucanie z czatu.
- powiadomienia o wiadomości na czacie
	https://dev.pippi.im/writing/build-github-like-notifications-with-django-messages-and-angular-js/ - Message Framework, to się wydaje fajne
	https://stackoverflow.com/questions/64768807/how-can-i-get-unread-messages-for-each-user - standardowy sposób z modelem
	https://evileg.com/en/post/418/ - tutorial
	https://github.com/django-notifications/django-notifications - jakiś moduł
- Pole tekstowe rośnie https://stackoverflow.com/questions/7168727/make-html-text-input-field-grow-as-i-type https://stackoverflow.com/questions/67960185/how-to-make-a-input-field-expand-vertically-and-not-horizontally-when-you-type
- Możliwość oznaczania wypowiedzi jako predykcji. Powinno dać się datę przypomnienia albo wydarzenie po którym będzie można sprawdzić tą predykcję.
- nie działa na safari. Automate cross browser testing. ReferenceError can't find variable TRANSLATION on Safari

1. Consolidate JavaScript Files:
Currently, chat-related JavaScript is spread across multiple files (chat.js, templates.js, utility.js, notifications.js)
Consider combining these into a single chat.js file or at least organizing them better in a chat/ directory
This would make the code more maintainable and reduce the number of HTTP requests

2. Simplify Room Management:
The Room model has many fields and relationships that could be simplified
Consider removing the seen_by and muted_by M2M fields and replacing them with a single RoomUserPreference model
This would make the model cleaner and easier to maintain

3. Streamline Message Handling:
The message template in templates.js is quite complex with many conditional elements
Consider splitting it into smaller, reusable components
The voting system could be moved to a separate component

4. Improve CSS Organization:
The chat.css file has many hardcoded values and could benefit from CSS variables
Consider organizing styles into logical sections (layout, messages, rooms, etc.)
Remove commented-out code and unused styles

5. Simplify WebSocket Communication:
The ChatConsumer class has many methods and complex logic
Consider splitting it into smaller, focused classes (e.g., MessageHandler, RoomHandler)
The message formatting logic could be moved to a separate service

6. Template Structure:
The chat.html template has duplicate code for public and private sections
Consider creating reusable template components for common elements
The archive toggle functionality could be simplified

7. Database Optimization:
The Message model has a complex unique constraint that might be unnecessary
Consider simplifying the voting system to use a single table with a vote type field
Add proper indexes for frequently queried fields

8. Code Organization:
Move all chat-related static files to a dedicated chat/static/chat/ directory
Consider using a proper frontend framework (like React or Vue) for the chat interface
This would make the code more maintainable and easier to test

9. Error Handling:
Add proper error handling for WebSocket connections
Implement retry mechanisms for failed operations
Add proper logging for debugging

10.  Performance Improvements:
Implement message pagination to reduce initial load time
Add caching for frequently accessed data
Optimize database queries in the consumer

CHAT2

Mobile API Documentation
Endpoints:

    /chat2/api/rooms/ - List and create rooms
    /chat2/api/messages/ - List and send messages
    /ws/chat2/<room_id>/ - WebSocket connection for real-time messages

WebSocket Example:

// JavaScript example
const socket = new WebSocket(
    'ws://' + window.location.host + '/ws/chat2/1/'
);

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    console.log(data);
};

// Send a message
socket.send(JSON.stringify({
    'type': 'message',
    'content': 'Hello, world!'
}));

# EMAILE
- język w emailach ustawiony na sztywno - niezależnie od przeglądarki wysyłającego formularz zapisywania się
  - funkcja wysyłające emaile powtarza się 6 razy. Może moduł z multitreading? https://anymail.dev/en/v12.0/tips/django_templates/ 
- opcja wyłączenia powiadomień email
    - Konfigurowalna częstotliwość wysyłania powiadomień o nowych zdarzeniach (czat, niektóre etapy referendów, prośba o dołączenie, )

# GŁOSOWANIA
- Głosowania stałe nad parametrami systemu (ile podpisów pod wnioskiem, czas trwania dyskusji, itd.)
- 1 dzień przerwy pomiędzy końcem zbierania podpisów a możliwością wycofania podpisu
- fixtures: Przywrócić startowe referenda
- Dodać pole: ten przepis powinien być stosowany jeśli (czas, warunek)
- Imienne dodawanie argumentów za i przeciw
- podświetlanie guzików kiedy jest trwające referendum
- te same kolory na guzikach co na obrazku
- Pokazywać kto podpisał wniosek o referendum
- Zegarek odliczający czas do końca referendum
- oprogramować powiadomienia o składce
- Pozytywy, negatywy referendum - każdy może komentować oba?
- Opis przy dodawaniu nowego przepisu: Co takiego się dzieje, przepis jest potrzebny; W jaki sposób to się dzieje, jaki jest mechanizm; Jak to zmienić żeby było lepiej; Jakie będą konsekwencje tej zmiany
- Szablony głosowań: sojusz z inną grupą (spięte z wymianą kluczy i danych pomiędzy grupami), wymagana reputacja (spięte z obywatele), czas trwania referendum (spięte z głosowania), zrzutka (spięte z rozliczaniem zrzutki), archiwizacja pokoi, wybory skarbnika, customowe (każde inne bez automatyzacji),

# HOME
- imię, nazwisko, username from email, miasto
- Zgoda na warunki przed przystąpieniem do grupy (grupa jawna/tajna do custom_settings)
- GROUP_IS_PUBLIC oprogramować
- Formularz zapisywania się nie zapisuje danych
- fixtures: Start i Footer do startowych fixtures
- do start dodać "ostatnie wiadomości na czacie" - za trudne. Trzeba poprawić cały czat

# LIBRARY
- Dodać ocenianie książek
- autor i tytuł zamiast obrazka zastępczego
- eBiblioteka - tagi + rating stars + recenzja/opis
- Wiki: assets - załączanie dowolnej ilości plików + galeria okładka książki + autor + gatunek + tagi + rating stars + czas wygasania + później player audio wideo + nft? + jeśli nft to ile jest sztuk + kto obecnie przechwuje (potwierdzenie od nadawcy i odbiorcy) 

# OGŁOSZENIA / BOARD
- Start i Footer powinny być opcjami w podczas edycji ogłoszenia
- Dodać komentarze pod artykułami (albo jeszcze lepiej - czat room)
- Powiadomienia email przy zmianie treści artykułu ale tylko przy okazji innych wiadomości
- Edytowanie ogłoszeń tylko przez autora
  - Zmiana autora jeśli ktoś zostanie wyrzucony z grupy
  - Ocenianie artykułów. Najniżej oceniane trafiają do ukrytego archiwum.

# OBYWATELE
- Dodać zmienne (liczby) do opisu https://polska.wikikracja.pl/obywatele/parameters/
- Banowanie użytkowników na określony czas. Trzeba dodać kilka stanów w których może znajdować się user. Będą to: zbanowany czasowo, zbanowany na stałe, członek honorowy bez prawa głosu (obserwator z zewnątrz)
- To tłumaczenie podczas samodzielnego zakładania konta nie działa: templates/allauth/account/messages/email_confirmation_sent.txt
- Próg akceptacji (chwilowy i przegłosowany)
- Dodawanie prywatnych notatek do osoby w Wikikracji
- Potwierdzenie konta za pomocą SMSa
- Dodać losowanie osoby, która będzie sprawowała daną funkcję
- Ograniczenie praw osobom, które mają być wyrzucone
  - zmiane emaila, nazwiska i użytwkonika przenieść do jednego formularza
  - Możliwość dodawania własnych pól w Zasobach
- Ochrona czasowa. Banowanie poprzedzić możliwością rozmowy z osobą
  
# INNE
- "Ostatnie logowanie" nie działa jeś  - do formularza wstępnego
  - Czy jesteś zwolennikiem DB?
  - Czy zgadzasz się na przestrzeganie naszych zasad?li ktoś się nie wylogował. Powinno być ostatnie kliknięcie.
- Wyślij wiadomość do całej grupy
- na komórce nie widać kto jest obecny (pogrubienie)
- dodać opis Wikikracji wszędzie gdzie się da. Uwzględnić emocje i błędy poznawcze. 
  - Grupy do skontaktowania się:
    - Śląski Związek Pszczelarzy (Zbigniew Bińko)
    - Ruch Autonomii Śląska
- czy można spowrotem włączyć apparmor? (proxy, wiki, jitsi)
- przenieść scripts do oddzielnego repo
- włączyć FireWall na wszystkich domowych maszynach
- Zastępowanie zmiennych ich wartościami: envsubst < config.txt > confidential_config.txt
- Mapa ze społecznościami. Zlinkować te grupy, które są otwarte.
- https://web.dev/what-are-pwas/ - da się zrobić aplikację na androida. Trzeba tylko zaszyfrować bazę, wystawić do niej api i wlić ją pomiędzy urządzeniami. Albo wystawić bazę na serwerze.
- Nie można należeć do dwóch geograficznych grup ale może istnieć więcej niż jedna geograficzna grupa dla danego obszaru. To po to żeby wyrzucone osoby mogłby zbudować swoją lepszą geograficzną grupę dla tego samego obszaru z którego te osoby zostały wyrzucone.
- Light and Dark mode https://youtu.be/n3lcjY4Mm00
- Formularz kontaktowy - napisz do grupy
- signal-cli do wysyłania wiadomości
- oferuje/potrzebuje do oddzielnej tabelki <- wiele do wielu -> Obywatel. Możliwość wyszukania istniejącej opcji i dodania nowej.
- firma do oddzielnej tabelki <- wiele do wielu -> Obywatel
- Powiadomienia i głosowania SMS
- PiotrCOHOTO może pomóc z wyglądem
- link obywatele zmienić na ludzie
- Tłumaczenie: "No file chosen" "Choose File" - https://stackoverflow.com/questions/14340519/html-input-file-how-to-translate-choose-file-and-no-file-chosen
- Do bloga dodać przewijanie artykułów
- burger menu na dół i sticky
- Django-WebRtc
- Dodać komunikat, jeśli użytkownik odzyskuje hasło ale nie ma ustawionego żadnego emaila
- Pozbyć się linka admin
- Legislator: opis kompetencji. Admin: superuser + opis kompetencji. Sędzia: read only + opis kompetencji. Django recuring payments module -stripe. Potrzebna jest najpierw rola Skarbnik.
- Wyłączyć edycję przepisów przez administratora
- Jak zoptymalizować wszystko o rząd wielkości?
	- przy zakładaniu konta dla grupy podaj zakres adresów np. Wrzeciono 57A / 1 - 30
	- pre-definiowane głosowania
- Dodać tytuł propozycji w emailach w tytule i treści
- Powiadomienie o nowym logowaniu (np. z nowego urządzenia)
- Administrator (konfiguracja systemu wedle wytycznych), sędzia (weryfikacja czy przepisy są realizowane), senator (tworzenie przepisów), skarbnik (trzyma kasę i magazyn): opisać ich role, ustawić jako argumenty dla ludzi
- Do woli: Jeśli dostajesz minusy a mimo to nie przyznajesz się do błędu to dostajesz dużego Minusa. Ale jeśli po dłuższym czasie WIĘKSZOŚĆ przyzna, że Miałeś rację to dostajesz ogromnego plusa. Wielkość plus jest proporcjonalna do czasu jaki upłynął od pierwotnej opinii. Takie podejście będzie premiowało to czy i, który z uczestników typuje z większym wyprzedzeniem przyszłe wydarzenia. Ci, których przewidywania się nie sprawdziły będą wraz z upływem czasu tracili na wartości (po to aby zachęcić do przyznawania się do błędu - przyznanie zatrzymuje licznik).
- settings.SECURE_SSL_HOST
- https://beeware.org/
- pycryptodome==3.6.1 > 3.6.6 ale to czeka na upgrade djangosecure z 0.0.11 na coś nowszego.
- Emaile nie są tłumaczone na angielski
- 2021-02 Generowanie userów na podstawie listy mieszkańców, listy emaili, numerów mieszkań. Kod zapraszający wygenerowany z konta osoby zapraszającej. Można podać fejkowy email i w ten sposób wygenerować hasło. Kliknięcie kodu oznaczałoby zgodę itp. Trochę mi tego brakuje. https://django-registration.readthedocs.io/en/3.1.1/ + dodatkowe pole z kodem. Tutorial: https://dev.to/coderasha/create-advanced-user-sign-up-view-in-django-step-by-step-k9m
- Przykład sukcesu: https://wiadomosci.gazeta.pl/wiadomosci/7,114881,26810291,legalna-aborcja-w-argentynie-dzialaczki-kosciol-wiedzial.amp
- https://docs.djangoproject.com/en/dev/ref/clickjacking/ - ok Wrzuć nową wersję na stronę a potem: https://www.ponycheckup.com/result/
- Automatyczny newsletter. Moduł do zapisywania ważnych wydarzeń w momencie ich zaistnienia i wysyłania zbiorczej informacji raz na tydzień.
- doprowadzić do tego żeby superuser był zbędny czyli eliminacja tego co jest w ## After installation
- Refactoring - przetłumaczyć zmienne na angielski
- fail2ban
- Wyświetlać końcówkę adresu IP z którego loguje się użytkownik
- Konfederacja: 
	django-organizations https://django-organizations.readthedocs.io/en/latest/usage.html
	1. Załóż nową grupę lub zaloguj się do istniejącej
	2. Moje grupy
		required: django-organizations==2.0.0
		APPS: 'organizations',
		URL: path('invitations/', include(invitation_backend().get_urls())),
		URL: from organizations.backends import invitation_backend
- Akceptacja/nie - bez wchodzenia w osobę: https://www.reddit.com/r/django/comments/b3ow2b/_/
- Newsletter z ostatniego tygodnia (głosowania, czaty). Logowanie kluczowych czynności. Pokazywać jakie wydarzenia ostatnio miały miejsce na użytkownikach
- Okreswy automatyczny export wyników głosowań oraz listy użytkowników + wysyłka do wszystkich na email
- Możliwość wyświetlania listy osób, które podpisły się pod wnioskiem o referendum
- podpowiedzi z możliwymi przepisami i biznesami do zrobienia
- dodać kasowanie własnego konta
- Zrobić SaaS: https://github.com/tomturner/django-tenants
- Secure Cookies - rozdział security z 2 scoops
- Zalogowanie się w systemie oznacza zgodę na następujące warunki... Jeśli z którymś z nich się nie zgadzasz to zapytaj osobę z grupy dlaczego został tak sformułowany... Będąc członkiem grupy będziesz miał wpływ na te przepisy w dokładnie takim samym stopniu jak każdy inny obywatel.
- Prawa administratora nadajemy po wyborach. Podobnie sędzia i senator. Administrator realizuje przepisy. Sędzia kontroluje administratora i senatora. Senator musi znać przepisy i we współpracy z administratorem i sędzią tworzy nowe.
- Dodać informację, że podanie emaila jest niezbędne żeby otrzymać hasło

# NIE BĘDZIE ZROBIONE WILL NOT BE DONE FOR NOW
  - Flutter - aplikacja na Androida i IOS
  - Riot/Matrix integration. Odpada bo trzeba by tworzyć oddzielne konta na Riot dla użytkowników
  - pogrubić login w emailu - to jest w module venv/lib/python3.6/site-packages/django/contrib/admin/templates/registration/password_reset_email.htm
  - nasz człowiek w parlamencie
  - 2021-03 dodać ankiety do błahych decyzji - zamiast tego zrobić up_vote/down_vote do chatu - wypowiedź z największą ilością (większość?) up votów tworzy nowy pokój

------------------------------------------------------------

# ZROBIONE
- Dobrowolny formularz dla nowej osoby, która sama się zapisuje. Adnotacja: "Wszystkie pola są dobrowolne. Potrzebujemy tego ponieważ nic nie wiemy o nowych osobach." Pola w formualrzu:  dlaczego chcesz należeć do grupy, imię, nazwisko, telefon, miasto, zawód, hobby, biznes, umiejętności, wiedza.
- Zadania - małe guziczki za/przeciw w widoku listy.
- Jeśli ktoś próbuje zapisać się do grupy po raz drugi (na ten sam email) to powinien dostać infomrację, że jego kandydatura jeszcze jest w kolejce.
- Do Start dodałem Zadania w realizacji i nowe nowe wiadomości na czacie