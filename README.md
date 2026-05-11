
# HEARTH BUYS Real App

This is a real local backend starter app with:

- Customer sneaker submission form
- Multiple image uploads
- SQLite database storage
- Admin master login
- Admin dashboard
- View submissions and photos
- Update status: Pending, Accepted, Quoted, Rejected
- Add quote amount and admin notes

## Run locally

```bash
cd hearth_buys_real_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open:

- Seller website: http://127.0.0.1:5000
- Admin dashboard: http://127.0.0.1:5000/admin

## Default admin login

Username:

```text
admin
```

Password:

```text
JordanBuys2026!
```

Change before going live.

## Production notes

For a real public launch, deploy to Render, Railway, Fly.io, or a VPS.

Before going live:
- Set `SECRET_KEY`
- Set `ADMIN_USERNAME`
- Set `ADMIN_PASSWORD`
- Use Postgres instead of SQLite
- Use cloud file storage for photos
- Add email notifications
- Add HTTPS and a custom domain
