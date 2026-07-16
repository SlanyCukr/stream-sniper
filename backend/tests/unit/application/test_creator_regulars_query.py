"""Contract tests for creator-regulars application orchestration."""

from unittest.mock import Mock

from stream_sniper.application.creators.regulars_query import CreatorRegularsSources, get_creator_regulars
from stream_sniper.database.gateways.creators.records import CreatorRegularRow


def test_query_coordinates_sources_and_calculates_attendance() -> None:
    count_streams = Mock(return_value=8)
    select_regulars = Mock(
        return_value=[
            CreatorRegularRow(42, "chatty", 6, "first", "last", 99, 1250),
        ]
    )

    result = get_creator_regulars(
        5,
        2,
        50,
        CreatorRegularsSources(count_streams, select_regulars),
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


def test_query_uses_zero_attendance_when_creator_has_no_streams() -> None:
    row = CreatorRegularRow(42, "chatty", 3, "first", "last", 99, 1250)
    result = get_creator_regulars(
        5,
        2,
        50,
        CreatorRegularsSources(lambda _creator_id: 0, lambda *_args, **_kwargs: [row]),
        sort="attendance",
        direction="desc",
        include_bots=False,
    )

    assert result.regulars[0].attendance_rate == 0.0
