# Usage Guide

## First run

1. Open the app (http://localhost:8000).
2. **Sign up** with an email, name and a password (min 8 chars, letters + numbers).
3. You land on the dashboard with zeroed stats.

## Demo data

```bash
python seed.py
```
→ creates `demo@hisab.pk` / `demo1234` with 3 clients, 3 invoices (sent / overdue / paid).

## Daily workflow

1. **Add a client** — Clients → Add Client (name required; company/email/country optional).
2. **Create an invoice** — Dashboard → + New Invoice. Pick the client, currency, due date,
   and add line items (description, qty, unit price). Totals + 5% tax are auto-calculated.
3. **Send it** — Invoices → Send. Status becomes `sent`.
4. **Get paid** — Invoices → Mark paid. Status becomes `paid`. If the due date passes while
   still `sent`, the invoice flips to `overdue` automatically.
5. **Check your income** — Income Report shows USD totals and the outstanding PKR estimate.

## Ownership & safety

- Every client and invoice belongs to the logged-in user. You cannot see or touch another
  account's data — the API enforces owner scoping on every query.
- Deleting a client with existing invoices is blocked (delete the invoices first).
- Deleting is permanent — there's a confirmation dialog in the UI.
