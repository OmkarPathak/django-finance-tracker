# Double-Entry Rollout Plan (No UX Change)

## Goal
Introduce a double-entry ledger behind the scenes while keeping current user workflow unchanged.

Users should continue to use the same screens:
- Add expense
- Add income
- Transfer between accounts
- Record loan repayment

No debit/credit terminology should be exposed in UI.

---

## Principles
1. No UX regression: forms, URLs, and page flow remain unchanged.
2. Backward-compatible rollout: current models keep working during transition.
3. Safety first: feature flags, reconciliation, and rollback at each phase.
4. Immutable accounting: ledger entries are append-only.
5. Idempotent posting: retries must not create duplicate ledger entries.

---

## Current State Summary
Current balance logic mutates account balances directly in model save/delete methods.
This is fast but harder to audit and reconcile at scale.

The migration plan below adds ledger as source-of-truth gradually while preserving existing behavior.

---

## Target Architecture

### New Core Models
1. LedgerAccount
- user (nullable for system-level accounts)
- code (unique)
- name
- type (ASSET, LIABILITY, INCOME, EXPENSE, EQUITY)
- currency (optional if multi-currency per line)
- is_active

2. JournalEntry
- user
- posted_at
- source_type (EXPENSE, INCOME, TRANSFER, LOAN_REPAYMENT, ADJUSTMENT)
- source_id (id of source record)
- idempotency_key (unique)
- description
- metadata (json)
- status (POSTED, REVERSED)

3. JournalLine
- journal_entry
- ledger_account
- direction (DEBIT, CREDIT)
- amount
- currency
- fx_rate_to_base
- base_amount
- account_ref (optional FK to Account for reporting bridge)

4. Optional MaterializedBalance
- account
- currency
- balance
- updated_at
- maintained from journal lines only

### Posting Rules (High Level)
1. Expense (cash account)
- Debit Expense Category
- Credit User Asset Account

2. Income
- Debit User Asset Account
- Credit Income Source

3. Transfer
- Debit Destination Asset Account
- Credit Source Asset Account

4. Loan Repayment
- Debit Loan Liability (principal)
- Debit Interest Expense (interest)
- Credit Paying Asset Account (total)

All entries must balance in base currency.

---

## Feature Flags
Add flags in settings or DB-backed config:

1. LEDGER_WRITE_ENABLED
- Write journal entries for new transactions.

2. LEDGER_RECONCILE_ENABLED
- Run reconciliation jobs and emit alerts.

3. LEDGER_READ_ENABLED
- Read balances/reports from ledger for selected cohorts.

4. LEDGER_ENFORCE_BALANCED_WRITE
- Block transaction save if journal post fails.

Suggested rollout order:
- Start with LEDGER_WRITE_ENABLED off in prod.
- Enable for internal users first.
- Expand gradually after reconciliation confidence.

---

## Phased Plan

## Phase 0: Prep and Observability (1-2 days)
Scope:
- Add structured logging for all money mutations.
- Define SLOs and alerting for transaction failures.
- Add dashboards for posting latency and failures.

Deliverables:
- Log schema with correlation id and user id.
- Error budget and alert thresholds.

Exit criteria:
- Can trace any financial mutation across request logs.

---

## Phase 1: Ledger Schema and Posting Service (3-5 days)
Scope:
- Create models: LedgerAccount, JournalEntry, JournalLine.
- Create posting service with idempotency:
  - post_expense
  - post_income
  - post_transfer
  - post_loan_repayment
- Add balanced-entry validation in service.

Deliverables:
- Migrations for ledger models.
- Unit tests for balancing and idempotency.

Exit criteria:
- Posting service can create valid balanced journals in isolation.

---

## Phase 2: Shadow Writes (No Behavior Change) (4-7 days)
Scope:
- Keep existing balance mutation logic unchanged.
- After successful transaction save, write journal entry in same DB transaction where possible.
- Use idempotency key pattern: {source_type}:{source_id}:{version}
- Add reverse journal on delete/update where required.

Where to integrate:
- Expense model save/delete
- Income model save/delete
- Transfer model save/delete
- LoanRepayment save/delete
- Recurring processing path

Deliverables:
- Shadow posting hooks.
- Dead-letter table or retry queue for posting failures.

Exit criteria:
- New transactions produce both old-model effects and journal entries.
- No user-facing workflow changes.

---

## Phase 3: Reconciliation Engine (3-5 days)
Scope:
- Daily job per user/account:
  - Compare Account.balance vs ledger-derived balance.
  - Compare dashboard aggregates old vs ledger for selected windows.
- Store reconciliation results and drift amount.
- Alert on drift above threshold.

Deliverables:
- Management command: reconcile_ledgers
- Reconciliation report model/table.

Exit criteria:
- Drift rate below agreed threshold for 2 consecutive weeks.

---

## Phase 4: Ledger Read Pilot (3-6 days)
Scope:
- Enable LEDGER_READ_ENABLED for internal/test cohort.
- Read balances in account detail and dashboard from ledger computation/materialized balance.
- Keep old path available as fallback.

Deliverables:
- Read adapter service with switch:
  - get_account_balance(account_id)
  - get_net_worth(user_id)
- Side-by-side comparison logs.

Exit criteria:
- Pilot cohort shows no critical mismatches.

---

## Phase 5: Progressive Cutover (3-7 days)
Scope:
- Expand ledger-read cohort gradually.
- For high confidence paths, enable LEDGER_ENFORCE_BALANCED_WRITE.
- Stop direct balance mutation only after reconciliation confidence is stable.

Deliverables:
- Rollout playbook with percentage gates.

Exit criteria:
- 100% reads from ledger.
- Direct Account.balance writes removed or reduced to materialized updates from ledger only.

---

## Phase 6: Cleanup and Hardening (2-4 days)
Scope:
- Remove dead legacy branches.
- Tighten constraints.
- Add immutable journal protections.

Deliverables:
- Final architecture docs.
- Runbooks for support and incident response.

Exit criteria:
- Ledger is canonical source of truth.

---

## Data Migration and Backfill Strategy
1. Do not rewrite old rows first.
2. Start shadow writes for new transactions.
3. Backfill historical transactions in batches by date/user.
4. For each batch:
- Post journals
- Reconcile
- Mark batch verified

Backfill safety:
- Idempotent backfill keys
- Batch checkpoints
- Stop/resume support

---

## UX Impact Plan
Target UX impact: none.

Rules:
1. Keep all existing forms and endpoints.
2. Keep success/error messages user-friendly and unchanged where possible.
3. Do not expose accounting jargon.
4. If posting fails and enforcement is on, show simple actionable message:
- "Unable to save transaction right now. Please try again."

---

## Performance Considerations
1. Add DB indexes:
- JournalEntry(user, posted_at)
- JournalEntry(source_type, source_id)
- JournalEntry(idempotency_key unique)
- JournalLine(ledger_account, journal_entry)

2. Use bulk inserts for backfill.
3. Consider materialized balance table for fast reads.
4. Keep reconciliation async/offline.

---

## Testing Strategy
1. Unit tests
- Every posting template balances.
- Idempotency key prevents duplicate posts.

2. Integration tests
- Current CRUD flows create expected journal entries.
- Update/delete produce proper reversals.

3. Property tests (recommended)
- Sum(debits) == Sum(credits) per journal in base currency.

4. Regression tests
- Existing UX/API tests remain green.

5. Load tests
- Posting latency under peak traffic.

---

## Rollback Strategy
At each phase:
1. Disable LEDGER_READ_ENABLED first.
2. Disable LEDGER_ENFORCE_BALANCED_WRITE if needed.
3. Keep LEDGER_WRITE_ENABLED on or off depending on incident type.
4. Do not delete journal data during rollback.

Emergency mode:
- Revert to old read path immediately.
- Keep logging and reconciliation to diagnose.

---

## Suggested Task Breakdown
1. Add ledger models and migrations.
2. Build posting service with idempotency.
3. Add shadow-write hooks in transaction save/delete paths.
4. Add reconciliation command and report table.
5. Add feature-flagged read adapter.
6. Pilot rollout for internal users.
7. Gradual cohort expansion.
8. Final cutover and cleanup.

---

## Done Definition
1. No user workflow change.
2. Ledger write success rate >= 99.99% (or agreed target).
3. Reconciliation drift near zero and within threshold.
4. Support team has runbooks for debugging mismatches.
5. Finance-critical reports are ledger-backed.

---

## Notes for Your Current Codebase
Given your existing architecture, start with hybrid shadow mode.
Do not attempt a big-bang switch.

This provides immediate auditability benefits with minimal UX risk and controlled rollout.
