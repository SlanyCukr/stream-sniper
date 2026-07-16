"""Unit tests for the pure CSV/NDJSON export serializers (api/export_utils.py)."""

import json

from stream_sniper.api.transport.export_utils import csv_content, csv_response, iter_csv, iter_ndjson


class TestCsvContent:
    def test_header_and_rows(self):
        text = csv_content(
            ["phrase", "usage_count", "chatter_count"],
            [
                {"phrase": "gg wp", "usage_count": 22, "chatter_count": 15},
                {"phrase": "no way", "usage_count": 10, "chatter_count": 8},
            ],
        )
        assert text.splitlines() == [
            "phrase,usage_count,chatter_count",
            "gg wp,22,15",
            "no way,10,8",
        ]

    def test_quotes_commas_and_newlines(self):
        text = csv_content(
            ["nick", "text"],
            [{"nick": "a", "text": 'hello, "world"\nbye'}],
        )
        # stdlib csv quotes the field and doubles inner quotes.
        assert text == 'nick,text\r\na,"hello, ""world""\nbye"\r\n'

    def test_none_becomes_empty_field(self):
        text = csv_content(["name", "provider_id"], [{"name": "KEKW", "provider_id": None}])
        assert text.splitlines()[1] == "KEKW,"

    def test_empty_rows_is_header_only(self):
        assert csv_content(["a", "b"], []).splitlines() == ["a,b"]


class TestCsvResponse:
    def test_media_type_and_disposition(self):
        response = csv_response(["a"], [{"a": 1}], "stream_7_emotes.csv")
        assert response.media_type == "text/csv"
        assert response.headers["content-disposition"] == 'attachment; filename="stream_7_emotes.csv"'
        assert response.body.decode().splitlines() == ["a", "1"]

    def test_extra_headers_merged(self):
        response = csv_response(["a"], [], "f.csv", extra_headers={"X-Cache": "HIT"})
        assert response.headers["X-Cache"] == "HIT"
        assert response.headers["content-disposition"] == 'attachment; filename="f.csv"'


class TestIterNdjson:
    def test_one_json_object_per_line(self):
        rows = [
            {"id": 1, "text": "hello"},
            {"id": 2, "text": "world"},
        ]
        lines = list(iter_ndjson(rows))
        assert all(line.endswith("\n") for line in lines)
        assert [json.loads(line) for line in lines] == rows

    def test_unicode_kept_literal(self):
        (line,) = list(iter_ndjson([{"text": "čau KEKW"}]))
        assert "čau" in line  # ensure_ascii=False — no \u escapes

    def test_empty_input_yields_nothing(self):
        assert list(iter_ndjson([])) == []

    def test_lazy_generator(self):
        def rows():
            yield {"id": 1}
            raise AssertionError("must not be consumed eagerly")

        iterator = iter_ndjson(rows())
        assert json.loads(next(iterator)) == {"id": 1}


class TestIterCsv:
    def test_header_first_then_rows(self):
        chunks = list(
            iter_csv(
                ["id", "nick", "text"],
                [
                    {"id": 1, "nick": "a", "text": "hi"},
                    {"id": 2, "nick": "b", "text": "one,two"},
                ],
            )
        )
        assert chunks[0] == "id,nick,text\r\n"
        assert chunks[1] == "1,a,hi\r\n"
        assert chunks[2] == '2,b,"one,two"\r\n'

    def test_empty_rows_yields_header_only(self):
        assert list(iter_csv(["a", "b"], [])) == ["a,b\r\n"]
