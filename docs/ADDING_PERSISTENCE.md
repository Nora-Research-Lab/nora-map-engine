# Adding real persistence (Postgres / Supabase)

Today, `app/services/registry.py` keeps datasets, layers, and workspaces in
process memory (with workspaces additionally mirrored to local JSON files).
That's enough for a single-instance demo, but it's lost whenever the
instance restarts -- which happens on every redeploy, and on Render's free
tier, after periods of inactivity too.

To swap in real persistence:

1. **Pick a store.** Supabase (Postgres) is the natural fit since NORA
   Research Lab already uses it elsewhere -- but any Postgres works.
2. **Implement the same interface `_Repository` exposes**: `add`, `get`,
   `list`, `update`, `delete`. A `PostgresRepository` class backed by
   SQLAlchemy or `asyncpg` that implements those five methods is a drop-in
   replacement.
3. **Swap the module-level singletons** (`datasets`, `layers`, `workspaces`
   in `registry.py`) to instantiate your new class instead of
   `_Repository()`.
4. **Nothing else changes.** Every API route calls `registry.datasets.get(...)`,
   `registry.layers.add(...)`, etc. -- none of them know or care whether
   that's an in-memory dict or a database round-trip.
5. Do the same for raw file bytes: `app/storage/local.py` implements
   `StorageBackend` (`write`/`read`/`exists`/`delete`); write an
   `S3Storage` or `SupabaseStorage` class against the same interface and
   change `storage_backend` in your environment.

This separation (API routes -> registry/storage interfaces -> concrete
implementation) is why persistence can be added later without a rewrite.
