"""Contract tests for creator-regulars application orchestration."""

from unittest.mock import Mock

from stream_sniper.application.creators import regulars_query
from stream_sniper.application.creators.regulars_query import get_creator_regulars
from stream_sniper.database.gateways.creators.records import CreatorRegularRow


def test_query_coordinates_sources_and_calculates_attendance(monkeypatch) -> None:
    count_streams = Mock(return_value=8)
    select_regulars = Mock(
        return_value=[
            CreatorRegularRow(42, "chatty", 6, "first", "last", 99, 1250),
        ]
    )
    monkeypatch.setattr(regulars_query, "count_streams_db", count_streams)
    monkeypatch.setattr(regulars_query, "select_creator_regulars_db", select_regulars)

    result = get_creator_regulars(
        5,
        2,
        50,
        sort="attendance",
        direction="desc",
        include_bots=False,
    )

    assert result.creator_id == 5
    assert result.total_streams == 8
    assert result.regulars[0].attendance_rate == 0.75
    count_streams.assert_called_once_with(5)
    select_regulars.assert_called_once_with(
        5,
        2,
        50,
        sort="attendance",
        direction="desc",
        include_bots=False,
    )


def test_query_uses_zero_attendance_when_creator_has_no_streams(monkeypatch) -> None:
    row = CreatorRegularRow(42, "chatty", 3, "first", "last", 99, 1250)
    monkeypatch.setattr(regulars_query, "count_streams_db", lambda _creator_id: 0)
    monkeypatch.setattr(regulars_query, "select_creator_regulars_db", lambda *_args, **_kwargs: [row])

    result = get_creator_regulars(
        5,
        2,
        50,
        sort="attendance",
        direction="desc",
        include_bots=False,
    )

    assert result.regulars[0].attendance_rate == 0.0
