# Double-Entry Production Quick Commands

Use this for fast execution during production rollout.

## 1) Set Production Environment Variables

```bash
LEDGER_WRITE_ENABLED=true
LEDGER_ENFORCE_BALANCED_WRITE=true
LEDGER_READ_ENABLED=true
LEDGER_READ_COHORT_PERCENT=100
LEDGER_READ_COHORT_USER_IDS=
LEDGER_READ_EXCLUDE_USER_IDS=
LEDGER_RECONCILE_ENABLED=true
LEDGER_RECONCILE_ALERT_THRESHOLD=10.00
LEDGER_READ_COMPARE_ENABLED=true
LEDGER_READ_COMPARE_SAMPLE_RATE=1.0
```

## 2) Backup Database (Before Deploy)

PostgreSQL:

```bash
pg_dump "$DATABASE_URL" > backup_pre_ledger_cutover_$(date +%F_%H%M%S).sql
```

SQLite:

```bash
cp db.sqlite3 db_pre_ledger_cutover_$(date +%F_%H%M%S).sqlite3
```

## 3) Deploy + Run Cutover Commands

```bash
source env/bin/activate
python manage.py migrate
python manage.py backfill_ledger_opening_balances --dry-run --limit 10000
python manage.py backfill_ledger_opening_balances --limit 10000
python manage.py ledger_rollout_status
python manage.py run_ledger_maintenance --reconcile --threshold 0.01
```

## 4) Immediate Verification Commands

```bash
python manage.py retry_ledger_shadow_failures --limit 200
python manage.py reconcile_ledgers --threshold 0.01
python manage.py ledger_rollout_status
```

## 5) Recurring Scheduler Commands

Every 5-10 minutes:

```bash
python manage.py retry_ledger_shadow_failures --limit 200
```

Daily (or every few hours during first week):

```bash
python manage.py reconcile_ledgers --threshold 0.01
```

Combined maintenance option:

```bash
python manage.py run_ledger_maintenance --reconcile --threshold 0.01
```

## 6) Fast Rollback Toggles

If incident occurs, set:

```bash
LEDGER_READ_ENABLED=false
LEDGER_ENFORCE_BALANCED_WRITE=false
```

Then restart/redeploy app config.

## 7) Optional Pilot Instead of 100%

Use this if you decide to stage rollout:

```bash
LEDGER_READ_ENABLED=true
LEDGER_READ_COHORT_PERCENT=5
LEDGER_READ_COHORT_USER_IDS=123,456
LEDGER_READ_EXCLUDE_USER_IDS=999
```

## 8) One-Liner Health Sweep

```bash
source env/bin/activate && python manage.py retry_ledger_shadow_failures --limit 500 && python manage.py reconcile_ledgers --threshold 0.01 && python manage.py ledger_rollout_status
```
