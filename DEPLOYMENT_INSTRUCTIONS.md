# Instrukcje wdrożenia poprawek kategoryzacji pokoi czatu

## Problem
Pokoje czatu nie są prawidłowo kategoryzowane na produkcji. Pokoje mają polskie prefiksy ("Zadanie #", "Głosowanie #"), ale kod filtruje po angielskich prefiksach.

## Rozwiązanie
Zostały wprowadzone zmiany w kodzie, które:
1. Używają stałych angielskich prefiksów ("Task #", "Vote #") w tytułach pokoi
2. Filtrują pokoje po angielskich prefiksach (bez tłumaczenia)
3. Dodają komendę do aktualizacji istniejących pokoi

## Kroki wdrożenia na produkcji

### 1. Wdrożenie kodu
Wdróż następujące pliki na produkcję:
- `chat/views.py` (linie 80-88) - zmienione filtrowanie
- `tasks/models.py` (linie 74-76) - angielski prefiks w get_chat_room_title
- `glosowania/models.py` (linie 90-92) - angielski prefiks w get_chat_room_title
- `glosowania/signals.py` (linie 21-22, 69-70) - angielski prefiks w sygnałach
- `glosowania/views.py` (linie 227-231) - użycie metod z modelu
- `chat/management/commands/fix_room_titles.py` - nowa komenda

### 2. Uruchomienie komendy naprawczej
Po wdrożeniu kodu, uruchom komendę na serwerze produkcyjnym:

```bash
python manage.py fix_room_titles
```

Komenda automatycznie:
- Znajdzie wszystkie pokoje z prefiksem "Zadanie #"
- Zmieni je na "Task #"
- Znajdzie wszystkie pokoje z prefiksem "Głosowanie #"
- Zmieni je na "Vote #"
- Wyświetli podsumowanie zmian

### 3. Restart serwera
Po uruchomieniu komendy, zrestartuj serwer Django:

```bash
# W zależności od konfiguracji:
systemctl restart gunicorn
# lub
systemctl restart uwsgi
# lub
supervisorctl restart wikikracja
```

### 4. Weryfikacja
Po restarcie sprawdź:
1. Czy pokoje są prawidłowo kategoryzowane w interfejsie czatu
2. Czy linki do pokoi z Głosowań i Zadań działają poprawnie
3. Czy nowe pokoje są tworzone z angielskimi prefiksami

## Przykładowy output komendy

```
Updated: "Zadanie #1: test" -> "Task #1: test"
Updated: "Zadanie #2: przykład" -> "Task #2: przykład"
Updated: "Głosowanie #1: propozycja" -> "Vote #1: propozycja"
Updated: "Głosowanie #2: test" -> "Vote #2: test"

Total rooms updated: 4 (2 tasks, 2 votes)
```

## Co zostało zmienione

### Przed:
- Pokoje tworzone z tłumaczonymi prefiksami (zależnie od języka)
- Filtrowanie używało `_("Task #")` i `_("Vote #")` (tłumaczone w runtime)
- Niespójność między tytułami pokoi a filtrowaniem

### Po:
- Pokoje zawsze tworzone z angielskimi prefiksami "Task #" i "Vote #"
- Filtrowanie używa stałych stringów "Task #" i "Vote #"
- Spójność między tytułami pokoi a filtrowaniem

## Uwagi
- Komenda jest bezpieczna i można ją uruchomić wielokrotnie
- Jeśli nie znajdzie pokoi do aktualizacji, wyświetli odpowiedni komunikat
- Komenda nie usuwa ani nie modyfikuje treści wiadomości w pokojach
- Zmienia tylko tytuły pokoi
