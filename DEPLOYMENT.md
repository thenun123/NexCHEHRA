# Deploying NexCHEHRA — Render + Supabase + ImageKit

## 0. What changed in the code
- `config/settings.py` — DB now comes from `DATABASE_URL` (Supabase), falls back to local sqlite.
- `app/models.py` — new `Asset` table tracks every file living on ImageKit.
- `clients/imagekit_client.py` — all uploads/downloads go through this.
- `clients/flux_client.py`, `clients/kling_client.py` — generated images/videos are now
  pushed straight to ImageKit instead of saved to local disk.
- `app/routes.py` — product/reference image uploads go straight to ImageKit.
- All templates — `/static/...` references rewritten to `{{ static_url('...') }}`,
  which resolves to the ImageKit URL once migrated (falls back to local `/static/` otherwise).
- `migrate_static_to_imagekit.py` — one-time script, mirrors your whole `static/` folder
  (assets, css, images, js, outputs, uploads, vedio — every subfolder) into ImageKit.

## 1. Create Supabase project
1. supabase.com → New project.
2. Settings → Database → Connection string → **URI**, "Session pooler" (port 6543, not 5432 —
   Render's IPv4-only network needs the pooler).
3. Copy it into your local `.env` as `DATABASE_URL=postgresql://...`.

## 2. Create ImageKit account
1. imagekit.io → sign up → Developer options.
2. Copy Public Key, Private Key, URL endpoint into your local `.env`:
   ```
   IMAGEKIT_PUBLIC_KEY=...
   IMAGEKIT_PRIVATE_KEY=...
   IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_id
   ```

## 3. Run the migration locally (once)
```bash
pip install -r requirements.txt --break-system-packages
python migrate_static_to_imagekit.py
```
This uploads every file under `static/` to ImageKit preserving the folder structure
(`static/css/app.css` → `ik.imagekit.io/.../nexchehra/css/app.css`, etc.), and writes a
row per file into the `Asset` table in Supabase. Since the DB is already pointed at
Supabase (step 1), this data is what your live app will read at startup — you only run
this script once, not on every deploy.

Re-run any time you add new site assets (new css/js/images you commit to the repo);
it skips files already migrated unless you pass `--force`.

## 4. Push to GitHub, connect to Render
1. Push this repo to GitHub.
2. Render dashboard → New → Blueprint → point at the repo (picks up `render.yaml` automatically),
   or New → Web Service manually with:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
3. Set the env vars Render prompts for (`FAL_KEY`, `MISTRAL_API_KEY`, `DATABASE_URL`,
   `IMAGEKIT_PUBLIC_KEY`, `IMAGEKIT_PRIVATE_KEY`, `IMAGEKIT_URL_ENDPOINT`).
4. Deploy.

## Why this actually solves the "vanishes on refresh" problem
Render's disk is wiped on every redeploy/restart. Nothing in this app writes anywhere
that matters anymore once `IMAGEKIT_ENABLED` is true (all three env vars set):
- Generated portraits/videos → uploaded to ImageKit the moment fal.ai returns them.
- User-uploaded product/reference images → uploaded to ImageKit the moment they're received.
- Every file's URL + metadata → written to Supabase (Postgres), which is a separate
  managed service Render restarts can't touch.
- Site assets (css/js/images/vedio you built into the repo) → already safe on every
  redeploy since they come from git, but are *also* mirrored to ImageKit per your
  request, and templates fetch them from there via `static_url()`.

## Local dev without any of this set up
Leave `DATABASE_URL`/`IMAGEKIT_*` unset — the app falls back to sqlite +
local `static/` writes exactly like before, no code changes needed to keep developing locally.

## One caveat
`/api/logs/<session_id>` is a Server-Sent-Events stream (used for the live generation log).
Gunicorn's default sync worker can hold a long request per thread — the `--threads 4`
flag above covers small-scale usage. If you see logs stalling under real concurrent
traffic later, switch to `--worker-class gevent` (add `gevent` to requirements.txt).
