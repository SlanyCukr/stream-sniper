"""Scene-wide chat search: trigram + unaccent indexes on deduplicated text.

Backs GET /search/* (substring search over the whole scene). Match semantics are
`f_unaccent(lower(text)) LIKE '%needle%'`, so the supporting index must be built
over the SAME expression:

  * pg_trgm supplies the `gin_trgm_ops` operator class that makes an unanchored
    LIKE '%...%' index-backed instead of a full scan.
  * unaccent folds diacritics so a search for "cafe" also hits "café". The stock
    `unaccent(text)` is only STABLE (its dictionary can be reconfigured), which bars
    it from an index expression — so we wrap the two-argument, dictionary-pinned
    `public.unaccent('public.unaccent', text)` form in an IMMUTABLE SQL function.

Extensions install into `public` by default; every reference is schema-qualified so
this revision also emits correctly under offline (--sql) mode. This revision is fully
transactional (no CONCURRENTLY): message_text is ~134k rows in prod, so the GIN build
is fast and the brief lock is acceptable, and staying transactional keeps offline mode
working (unlike 0002/0004/0005).

Revision ID: 0017
Revises: 0016
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trusted extensions (PG13+); prod user has CREATE on the database. WITH SCHEMA
    # public is mandatory: migrations run with search_path=stream_sniper (env.py), so
    # a bare CREATE EXTENSION would install into stream_sniper and every
    # public.-qualified reference below would fail.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public")

    # IMMUTABLE wrapper: pins the dictionary argument so the expression is safe to
    # index. STRICT (NULL in -> NULL out), PARALLEL SAFE for parallel scans.
    # The dictionary argument is cast to ::regdictionary explicitly: without it the
    # bare 'public.unaccent' literal stays `unknown` during body validation and fails
    # to resolve the two-arg overload ("function public.unaccent(unknown, text) does
    # not exist"). The cast pins it to the dictionary object at creation time.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION stream_sniper.f_unaccent(text)
        RETURNS text AS
        $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        """
    )

    # GIN trigram index over the exact match expression used by the search gateway.
    op.execute(
        "CREATE INDEX IF NOT EXISTS message_text_trgm_idx "
        "ON stream_sniper.message_text "
        "USING gin (stream_sniper.f_unaccent(lower(text)) public.gin_trgm_ops)"
    )

    # Btree to join matched text ids back into message, newest-first per text.
    # No equivalent exists: 0004/0005 index (stream_id, ...) and (chatter_id, ...),
    # neither leads with message_text_id.
    op.execute(
        "CREATE INDEX IF NOT EXISTS message_text_id_time_idx "
        "ON stream_sniper.message (message_text_id, time)"
    )


def downgrade() -> None:
    # Drop indexes + function; leave the extensions installed (other objects may
    # come to rely on them, and dropping shared extensions is disruptive).
    op.execute("DROP INDEX IF EXISTS stream_sniper.message_text_id_time_idx")
    op.execute("DROP INDEX IF EXISTS stream_sniper.message_text_trgm_idx")
    op.execute("DROP FUNCTION IF EXISTS stream_sniper.f_unaccent(text)")
