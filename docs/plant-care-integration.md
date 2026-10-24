# Plant Care integration

Work is on feat/plant-care; no automatic commit/push.

## Run

Activate `env`, install `requirements.txt`, run `python manage.py migrate`, then `python manage.py runserver`. Register/sign in with the existing `/register/` and `/login/`. Open `/plant-care/` or the Plant Care navbar link. Login honours safe same-host `next` URLs.

## Temporary data model — integration prerequisite

`care.GardenSpace` and `care.Plant` are temporary adapters from the starter, NOT the final My Plants/Garden Setup modules. The supplied Auth/Journal code contains no official plant model. Do not release this as final cross-module integration. Agree the official model with those owners; update FK, owner queries, timezone/location access, forms, tests and seed command. If this migration has been applied/shared, create follow-up schema/data migrations instead of deleting migration history. Journal plant_name is text, not a shared plant identifier.

## Try with sample plants

No plants/accounts are created automatically. To populate an existing local account for a demonstration:

```powershell
python manage.py seed_terrapeer --username YOUR_EXISTING_USERNAME
```

The command creates sample plants and care tasks for that account. Use a dedicated local demo account if you want sample data separate from your own. Empty state is expected before plants exist.

## Weather

Live Open-Meteo is the default, with timeout/cache and unavailable state. For a labelled demo, set `WEATHER_DEMO=1` in your local .env and restart; remove it for live data. Never commit .env.

## UI and shared CSS

Keep the care page on `terrapeer/base.html` for now: it loads `shared.css` and `plant-care.css` only. Auth/landing keep `base.html` and `css/style.css`. This prevents conflicting .hero/.brand selectors and duplicated navbars. Existing auth pages have not been redesigned. Home returns to the group's landing; Journal link appears only when its named URL exists. No Edit Space forms or dead demo navigation anchors were introduced. Landing dashboard integration is a separate task.

## Check before PR

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test care
```

Review changed files in VS Code Source Control, stage selected files, commit, then Publish Branch/Push when ready. PR base: main. Exclude env, .env, db.sqlite3 and __pycache__; include migrations. Do not merge the temporary model into final production without agreeing its replacement.

## Verification on 24 October 2026

26 care backend tests and 4 project integration tests passed. Browser QA used a separate shared in-memory database and labelled weather demo: existing login, task create/reload, validation, filters, recurring completion, deletion, mobile overflow and JavaScript errors checked successfully. Live forecast network was not verified. Local care migration applied; no sample data added to the user database. Changes remain uncommitted.
