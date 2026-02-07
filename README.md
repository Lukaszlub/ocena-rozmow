# System Oceny Rozmow Telefonicznych

Minimalny projekt startowy (MVP) do automatycznej oceny rozmow MP3:
- ingest plikow (watcher)
- transkrypcja (OpenAI Audio API)
- ocena wg wag (LLM + JSON schema)
- wykrywanie wulgaryzmow
- zapis do bazy (SQLite) + opcjonalny eksport do Excela

## Szybki start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY = "twoj_klucz"
python -m src.app.main --mode watch
```

## Struktura
- `src/app/main.py` - punkt wejscia (watcher / batch)
- `src/pipelines/` - pipeline przetwarzania
- `src/services/` - uslugi (stt, scoring, profanity, db, export)
- `src/core/` - konfiguracja i modele danych
- `data/incoming` - nowe mp3
- `data/invalid` - bledne nazwy
- `data/processed` - przetworzone
- `reports` - eksporty Excel

## Konfiguracja
Zmien w `config.yaml`:
- foldery wejsciowe
- wagi kategorii
- slownik wulgaryzmow
- modele i parametry OpenAI
- sciezka bazy SQLite

## Uwagi
- Transkrypcja korzysta z OpenAI Audio API (modele `gpt-4o-mini-transcribe` / `whisper-1`).
- Scoring korzysta z Responses API i Structured Outputs (JSON schema).
- Dla lokalnego LLM (LM Studio) ustaw `scoring.provider: lmstudio` i `scoring.base_url`.

## GUI (Tkinter)
Uruchom:
```powershell
python -m src.app.main --mode gui
```
Funkcje:
- wybór plikow MP3 do oceny
- podglad postepu oceny
- podsumowanie wynikow
- podglad szczegolow oceny i transkrypcji
- filtrowanie po nazwie konsultanta
- paginacja historii
- cytat wykrytego wulgaryzmu w tabeli

