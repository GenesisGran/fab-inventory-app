**FAB Inventory Tool**

Live demo: https://fab-inventory.streamlit.app/

Why
---
FAB Inventory Tool is a secure, invite-only collection manager for Flesh and Blood
players. It provides a minimal, focused UX for recording single or bulk card
updates while relying on Supabase Row Level Security (RLS) and an invite
registration gate to reduce spam and protect user data.

Architecture Highlights
-----------------------
- Frontend: Streamlit app (`input_inventory.py`) running on Streamlit Cloud.
- Backend: Supabase (Postgres) with Row Level Security (RLS) to enforce per-user
  access to inventory rows.
- Secrets: Supabase URL and keys are stored in Streamlit Secrets and never
  embedded in source control.
- Roles: The app uses the Supabase "anon" key for typical reads/writes and a
  service/admin key (kept secret) for server-side operations such as creating
  users and burning invite keys. The service key is only read from Streamlit
  Secrets at runtime and never shown in the UI.

Technical Features
------------------
- Single Add: Add/adjust a single `print_id` with foil and quantity delta.
- Bulk Add: Paste a simple batch (ID FOIL QTY) to process many updates at once.
- Custom CSS "Vault" theme: Forces a dark UI and restyles controls to prevent
  light-mode overrides and to provide a consistent branded look.
- Invite-only registration: Admins create single-use invite keys. When a
  user registers, the invite key is marked used (burned) to prevent reuse.
- Supabase + RLS: The app relies on database-side RLS policies to restrict row
  operations to the owning user, reducing the amount of trust placed on the
  frontend code.

Setup
-----
1. Create a Streamlit Cloud app or run locally.
2. Provide Streamlit Secrets with at least:

```toml
[secrets]
SUPABASE_URL = "https://..."
SUPABASE_KEY = "anon-public-key"
# Optional: SUPABASE_SERVICE_KEY = "service-role-key"
```

3. Install requirements and run locally:

```bash
pip install -r requirements.txt
streamlit run input_inventory.py
```

Security Notes
--------------
- Do not commit secret keys to source control. Use Streamlit Secrets or a
  secure secrets manager.
- The service/admin key has elevated privileges. Keep it restricted and only
  present in the runtime environment (Streamlit Secrets or CI/CD secrets).
- RLS is the primary protection for user data — check your Supabase RLS
  policies to ensure users can only access their own rows.

Files
-----
- `input_inventory.py`: Main Streamlit app (refactored, typed, and documented).
- `requirements.txt`: Python dependencies.

If you'd like, I can add a short CONTRIBUTING section, a small architecture
diagram, or include CI checks (linting) to the repo next.
