from stream_sniper.database.core.query_ordering import sql_direction


def test_sql_direction_returns_only_fixed_fragments() -> None:
    assert sql_direction("asc") == "ASC"
    assert sql_direction("desc") == "DESC"
    assert sql_direction("DROP TABLE stream") == "DESC"
