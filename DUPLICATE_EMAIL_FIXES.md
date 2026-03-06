# Podsumowanie napraw problemów z duplikatami emaili

## Znalezione problemy i zastosowane poprawki

### 1. **Auth Backend** (`obywatele/auth_backends.py`)
**Problem**: `.get(email__iexact=...)` rzucał `MultipleObjectsReturned` gdy istniały duplikaty emaili.

**Poprawka**: Dodano obsługę wyjątku `MultipleObjectsReturned` - próbuje zalogować aktywnego użytkownika jeśli jest tylko jeden.

### 2. **Migracje danych**
**Utworzone migracje**:
- `0011_remove_duplicate_emails.py` - usuwa duplikaty użytkowników i czyści osierocone rekordy
- `0012_alter_user_email_unique.py` - dodaje constraint UNIQUE na pole email

**Co robi migracja 0011**:
- Usuwa osierocone rekordy `Uzytkownik` (gdzie `uid_id` nie istnieje)
- Usuwa osierocone rekordy we wszystkich tabelach z FK do User:
  - `MessageVote.user`
  - `Message.sender`
  - `Post.author`
  - `Book.uploader`
  - `Decyzja.author`
  - `Argument.author`
  - `ZebranePodpisy.podpis_uzytkownika`
- Usuwa osierocone rekordy `Rate` (kandydat/obywatel)
- Usuwa duplikaty użytkowników z tym samym emailem (zachowuje aktywnych, potem najnowszych)

### 3. **Signup Form** (`obywatele/forms.py`)
**Problem**: Brak obsługi błędów przy zapisie użytkownika.

**Poprawka**: Dodano try/except wokół `user.save()` - jeśli wystąpi błąd unique constraint, usuwa duplikat i używa istniejącego użytkownika.

### 4. **Sprawdzanie emaila** (`obywatele/views.py:381`)
**Problem**: Używał `email=mail` zamiast `email__iexact=mail`.

**Poprawka**: Zmieniono na `email__iexact=mail` dla case-insensitive porównania.

### 5. **Signal DeactivateNewUser** (`obywatele/views.py:702`)
**Problem**: `User.objects.get()` bez obsługi wyjątków.

**Poprawka**: Dodano try/except dla `DoesNotExist` i `MultipleObjectsReturned`.

### 6. **Signal save_user_profile** (`obywatele/models.py:68-69`)
**KRYTYCZNY PROBLEM**: Signal uruchamiał się przy każdym zapisie User i próbował zapisać `instance.uzytkownik.save()` nawet gdy Uzytkownik nie istniał.

**Poprawka**: Dodano sprawdzenie `if hasattr(instance, 'uzytkownik'):` przed zapisem.

### 7. **Niepotrzebne zapytanie do bazy** (`elibrary/views.py:26`)
**Problem**: Używał `User.objects.get(username=request.user.username)` zamiast `request.user`.

**Poprawka**: Zmieniono na bezpośrednie użycie `request.user`.

## Konfiguracja
W `zzz/settings.py` już jest ustawione:
```python
ACCOUNT_UNIQUE_EMAIL = True
```

## Jak wdrożyć na produkcji

1. **Wykonaj backup bazy danych**
```bash
kubectl exec -it wikikracja-instance-1-xxx -n wikikracja -- sqlite3 /app/db/db.sqlite3 ".backup /tmp/backup.db"
kubectl cp wikikracja-instance-1-xxx:/tmp/backup.db ./backup-$(date +%Y%m%d).db -n wikikracja
```

2. **Wdróż nowy kod**
```bash
git add .
git commit -m "Fix duplicate email issues and add unique constraint"
git push
```

3. **Migracje zostaną wykonane automatycznie** podczas startu kontenera

4. **Monitoruj logi**
```bash
kubectl logs -f wikikracja-instance-1-xxx -n wikikracja
```

## Co zostało naprawione

✅ Auth backend obsługuje duplikaty emaili
✅ Migracja usuwa istniejące duplikaty
✅ Constraint UNIQUE na email zapobiega nowym duplikatom
✅ Wszystkie miejsca używające `.get()` mają obsługę błędów
✅ Sprawdzanie emaili jest case-insensitive
✅ Sygnały Django nie powodują błędów przy brakujących relacjach
✅ Signup form obsługuje race conditions

## Potencjalne problemy do monitorowania

1. **Użytkownicy z duplikatami emaili** - po migracji zostaną usunięci nieaktywni/starsi
2. **Osierocone rekordy** - zostaną usunięte przez migrację
3. **Race conditions podczas rejestracji** - obsłużone przez try/except w signup form

## Testowanie lokalne

```bash
python manage.py migrate
python manage.py runserver
```

Spróbuj:
1. Zalogować się z różnymi wielkościami liter w emailu
2. Zarejestrować użytkownika z istniejącym emailem (powinien pokazać błąd)
3. Sprawdzić czy nie ma błędów 500 w logach
