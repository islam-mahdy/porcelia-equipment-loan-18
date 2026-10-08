# Porcelia Equipment Loan Manager

Odoo 19.0 Community module — `porcelia_equipment_loan`

Manages the full lifecycle of internal equipment loans: request → confirm →
return, with overlap protection, automatic late-return penalties, a manager
dashboard (OWL), a custom "Condition Gauge" field widget, and a daily
scheduled action for overdue detection.

## 1. Installation

```bash
# Copy (or clone) the module into your addons path, e.g.:
cp -r porcelia_equipment_loan /path/to/odoo/addons/

# Create the database and install the module with demo data:
odoo-bin -d assessment_db -i porcelia_equipment_loan --without-demo=False

# Restart / update after any further changes:
odoo-bin -d assessment_db -u porcelia_equipment_loan
```

No third-party Python packages are required beyond a standard Odoo 19
Community install.

### Running the tests

```bash
odoo-bin -d assessment_db -i porcelia_equipment_loan --test-enable --stop-after-init
```

This runs the 9 `TransactionCase` tests in `tests/test_equipment_loan.py`
(3 were explicitly required by the brief; the rest are supporting checks for
the same business rules — e.g. a "happy path" overlap and an on-time return
alongside the required negative cases).

## 2. What's implemented

- **Data model (A1)** — `equipment.category` (self-referencing hierarchy
  with `_parent_store`/`complete_name`, grouped `item_count`),
  `equipment.item` (sequence-based code, computed/stored `state`, grouped
  `total_days_on_loan`), `equipment.loan` (full field set, `mail.thread` +
  `mail.activity.mixin`).
- **Business rules (A2)** — overlap detection on confirm, date sanity
  constraint, unique code SQL constraint per company, penalty computation
  (`ceil` of late days × daily rate), full workflow with state validation,
  deletion guard via `@api.ondelete`.
- **Security (A3)** — `Equipment / User` and `Equipment / Manager` groups
  (Manager implies User), complete ACLs (Users cannot delete items), and a
  record rule restricting Users to their own loans (Managers see all).
  `sudo()` is used in exactly two places — reading the `ir.sequence`
  counters for item codes and loan references — and is commented in both
  spots; no other access-control bypass is used anywhere.
- **Views & menus (A4)** — list/form/search for loans (My Loans, Overdue,
  Active filters; group-by State/Item/Borrower; red decoration for overdue
  loans), kanban/list/form for items with a smart button to loans, a
  `res.users` form extension (via `xpath`, no view copy) with a smart
  button to that user's loans, and the `Equipment` menu root with
  Loans / Items / Dashboard / Configuration → Categories.
- **Wizard (A5)** — `equipment.loan.return.wizard`, usable from a single
  loan's "Return" button or from a multi-selection in the list
  (`active_ids`), applying the return date/condition/note to every selected
  loan.
- **Automation (A6)** — a daily `ir.cron` flags overdue confirmed loans,
  posts one chatter message and schedules one activity per loan. It is
  idempotent via the `is_overdue` / `reminder_sent` flags — a test runs the
  cron twice and asserts exactly one activity exists.
- **Report (A7)** — a QWeb "Loan Receipt" PDF, bound to the loan list/form
  action menu, supporting single and multi-record printing.
- **Data & tests (A8)** — sequences for item codes and loan references,
  demo data (3 categories, 5 items, 4 loans covering all four states), and
  unit tests for overlap rejection, penalty calculation, and the record
  rule.
- **OWL field widget (B1)** — `condition_gauge`, registered on
  `registry.category("fields")`, built on `standardFieldProps`, with its
  own template/SCSS, colour-coded segments, click-to-set in edit mode, and
  a guard against `false`/empty values.
- **OWL dashboard (B2)** — `equipment_dashboard` client action with KPI
  cards, a top-5 overdue table (row click opens the loan form via
  `useService("action")`), a reactive period filter, and loading/empty
  states. All figures come from a single backend call,
  `equipment.loan.get_dashboard_data(period)`.
- **Bonus** — a systray counter of the current user's overdue loans (B3,
  hidden when zero, opens a filtered list on click); a partial Arabic
  translation (`i18n/ar.po`) covering the main UI labels; grouped
  aggregation (`_read_group`) used everywhere a total is needed instead of
  Python loops.

## 3. What was deliberately skipped or simplified

Given the 5-day time box, these were the conscious trade-offs:

- **Multi-company depth**: `company_id` fields exist and the code-uniqueness
  constraint is per company, but company-based record filtering beyond
  Odoo's default multi-company rules was not added — this was judged lower
  priority than the core workflow/security/OWL work.
- **`equipment.item` state and maintenance/scrapped**: the brief asks for
  `state` to be "computed and stored, derived from whether a confirmed,
  unreturned loan exists," which only describes two of the four states.
  Assumption: `available`/`on_loan` are recomputed automatically from
  active loans, while `maintenance`/`scrapped` are manual overrides that
  the automatic computation does not clobber (the compute method returns
  early for those two states). This is implemented with a stored computed
  field with `readonly=False`, a documented, common Odoo pattern.
- **Dashboard "penalties in the period"**: filtered on `date_return` falling
  within the selected period (week/month/all), which was the most natural
  reading of "total penalties in the period."
- **Report styling**: the QWeb template is functional and uses the standard
  `web.external_layout` (company header, address, etc.) but has no custom
  CSS beyond Bootstrap utility classes — polish was deprioritised in favour
  of correctness and multi-record support.
- **Arabic translation**: covers the main visible UI strings used in
  practice (menus, states, buttons, dashboard) rather than every string in
  the module (a full `.pot` export was not generated).
- **No custom module icon** was added (`static/description/`), to keep the
  time budget on functional code.
- **Git history**: this deliverable was prepared as a complete module tree
  with an initial local commit; per the task's process note ("commit as
  you go"), a real submission would show incremental commits per section —
  here that history could not be produced after the fact, so it is called
  out rather than faked.

## 4. Assumptions

- "Grouped query" for `total_days_on_loan` and `loan_count`/`item_count` is
  implemented with `_read_group` on a stored `duration_days` field on the
  loan (itself computed from `date_start`/`date_due`/`date_return`), so the
  aggregation is a single SQL `SUM`/`COUNT`, not a Python loop.
  `duration_days` is defined as: 0 for draft/cancelled loans, otherwise the
  number of days between `date_start` and (`date_return` or `date_due`, or
  "now" if still open).
- The overlap check only considers other **confirmed** loans of the same
  item (draft/cancelled loans never block a booking, since they don't
  represent a real commitment).
- `days_late` uses `ceil()` of the elapsed time in days, floored at 0, per
  the exact formula in the brief.
- The return wizard is also reachable from the loan form's "Return" header
  button (`action_open_return_wizard`), not only from the list's
  multi-selection action menu, since a single-record return is the most
  common case.

## 5. Screenshots

Not included in this text deliverable — install the module and open
**Equipment → Items** (Condition Gauge widget on the item form) and
**Equipment → Dashboard** (KPI cards + top overdue table) to see both.

## 7. External JSON API (controllers/)

For external system integration, `controllers/main.py` exposes read-only
JSON endpoints under `/porcelia/api/`:

| Route | Description |
|---|---|
| `GET /porcelia/api/items` | List items. Filters: `state`, `category_id`, `limit`, `offset` |
| `GET /porcelia/api/items/<id>` | Single item |
| `GET /porcelia/api/loans` | List loans. Filters: `state`, `item_id`, `overdue`, `limit`, `offset` |
| `GET /porcelia/api/loans/<id>` | Single loan |

**Authentication** is API-key based, not session-based (these routes are
declared `auth="public"` at the routing level so no login cookie is
required), but every request is resolved to a real Odoo user via
`res.users.apikeys._check_credentials()` and executed in that user's
environment — never with `sudo()`. This means the existing record rule
still applies over HTTP exactly as it does in the backend: an Equipment
User's key only ever returns their own loans; a Manager's key returns all
of them.

Generate a key under **Settings → Users & Companies → Users → \<user\> →
Account Security → New API Key**, then:

```bash
curl -H "X-API-Key: <key>" "https://<host>/porcelia/api/loans?state=confirmed"
curl -H "X-API-Key: <key>" "https://<host>/porcelia/api/items/3"
```

A missing/invalid key returns `401`; a record hidden by the record rule
returns `404` (not `403`), to avoid confirming a loan's existence to a user
who isn't allowed to see it.

## 8. Module structure

```
porcelia_equipment_loan/
├── __init__.py
├── __manifest__.py
├── models/          equipment_category.py, equipment_item.py,
│                    equipment_loan.py, res_users.py
├── wizard/          equipment_loan_return_wizard.py (+ views)
├── controllers/     main.py (JSON API for external integration)
├── security/        equipment_groups.xml, equipment_loan_security.xml,
│                    ir.model.access.csv
├── views/           category / item / loan / res.users / dashboard views,
│                    menus
├── report/          QWeb report action + template
├── data/            ir.sequence + ir.cron
├── demo/            demo data
├── tests/           test_equipment_loan.py
├── static/src/      fields/condition_gauge, dashboard, systray (OWL 2)
└── i18n/            ar.po
```
