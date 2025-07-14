"""
Unit tests for creator table gateway functions.

Tests all creator-related database operations including:
- Creator insertion with conflict handling
- Creator selection by nick and ID
- Creator Twitch ID retrieval
"""

import pytest
from unittest.mock import Mock, patch

from stream_sniper.database.creator_table_gateway import (
    select_creator_twitch_id_db,
    select_creator_id_db,
    insert_new_creator_db,
    select_creators_db
)
from tests.conftest import create_test_creator


class TestCreatorTableGateway:
    """Test suite for creator table gateway functions."""

    def test_select_creator_twitch_id_db_success(self, db_cursor, sample_creator_data):
        """Test successful retrieval of creator Twitch ID."""
        # Create test creator
        create_test_creator(db_cursor, sample_creator_data)
        
        # Test function
        twitch_id = select_creator_twitch_id_db(sample_creator_data['nick'])
        
        assert twitch_id == sample_creator_data['twitch_id']

    def test_select_creator_twitch_id_db_not_found(self, db_cursor):
        """Test behavior when creator Twitch ID not found."""
        with pytest.raises(TypeError):  # fetchone()[0] on None raises TypeError
            select_creator_twitch_id_db('nonexistent_creator')

    def test_select_creator_id_db_success(self, db_cursor, sample_creator_data):
        """Test successful retrieval of creator ID."""
        # Create test creator
        creator_id = create_test_creator(db_cursor, sample_creator_data)
        
        # Test function
        result_id = select_creator_id_db(sample_creator_data['nick'])
        
        assert result_id == creator_id

    def test_select_creator_id_db_not_found(self, db_cursor):
        """Test behavior when creator ID not found."""
        result = select_creator_id_db('nonexistent_creator')
        assert result is None

    def test_insert_new_creator_db_success(self, db_cursor, sample_creator_data):
        """Test successful insertion of new creator."""
        # Test function
        creator_id = insert_new_creator_db(
            sample_creator_data['nick'],
            sample_creator_data['display_name'],
            sample_creator_data['profile_image_url'],
            sample_creator_data['twitch_id']
        )
        
        assert creator_id is not None
        assert isinstance(creator_id, int)
        
        # Verify creator was inserted
        db_cursor.execute("SELECT * FROM creator WHERE id = %s", (creator_id,))
        creator = db_cursor.fetchone()
        
        assert creator is not None
        assert creator[1] == sample_creator_data['nick']  # nick column
        assert creator[2] == sample_creator_data['display_name']  # display_name column

    def test_insert_new_creator_db_conflict_handling(self, db_cursor, sample_creator_data):
        """Test that insert handles conflicts gracefully (ON CONFLICT DO NOTHING)."""
        # Insert creator first time
        first_id = insert_new_creator_db(
            sample_creator_data['nick'],
            sample_creator_data['display_name'],
            sample_creator_data['profile_image_url'],
            sample_creator_data['twitch_id']
        )
        
        # Insert same creator again - should return existing ID
        second_id = insert_new_creator_db(
            sample_creator_data['nick'],
            'Different Display Name',  # Different data
            'https://different-url.com/profile.jpg',
            sample_creator_data['twitch_id']
        )
        
        assert first_id == second_id
        
        # Verify only one creator exists
        db_cursor.execute("SELECT COUNT(*) FROM creator WHERE nick = %s", (sample_creator_data['nick'],))
        count = db_cursor.fetchone()[0]
        assert count == 1

    def test_select_creators_db_success(self, db_cursor):
        """Test successful retrieval of all creators."""
        # Create multiple test creators
        creators_data = [
            {'nick': 'creator1', 'display_name': 'Creator One', 'profile_image_url': 'url1', 'twitch_id': '111'},
            {'nick': 'creator2', 'display_name': 'Creator Two', 'profile_image_url': 'url2', 'twitch_id': '222'},
            {'nick': 'creator3', 'display_name': 'Creator Three', 'profile_image_url': 'url3', 'twitch_id': '333'}
        ]
        
        created_ids = []
        for creator_data in creators_data:
            creator_id = create_test_creator(db_cursor, creator_data)
            created_ids.append(creator_id)
        
        # Test function
        result = select_creators_db()
        
        assert len(result) == 3
        
        # Verify data structure (should return id, display_name)
        for i, creator in enumerate(result):
            assert len(creator) == 2  # id, display_name
            assert creator[0] == created_ids[i]  # id
            assert creator[1] == creators_data[i]['display_name']  # display_name

    def test_select_creators_db_empty(self, db_cursor):
        """Test behavior when no creators exist."""
        result = select_creators_db()
        assert result == []


class TestCreatorTableGatewayWithMocks:
    """Test creator table gateway functions with mocked database connections."""

    def test_select_creator_twitch_id_db_with_mock(self, mock_connection_pool):
        """Test select_creator_twitch_id_db with mocked database."""
        mock_pool, mock_connection, mock_cursor = mock_connection_pool
        mock_cursor.fetchone.return_value = ('123456789',)
        
        result = select_creator_twitch_id_db('test_creator')
        
        assert result == '123456789'
        mock_cursor.execute.assert_called_once_with(
            "SELECT twitch_id FROM creator WHERE nick = %s", 
            ('test_creator',)
        )

    def test_select_creator_id_db_with_mock(self, mock_connection_pool):
        """Test select_creator_id_db with mocked database."""
        mock_pool, mock_connection, mock_cursor = mock_connection_pool
        mock_cursor.fetchone.return_value = (42,)
        
        result = select_creator_id_db('test_creator')
        
        assert result == 42
        mock_cursor.execute.assert_called_once_with(
            "SELECT id FROM creator WHERE nick = %s", 
            ('test_creator',)
        )

    def test_select_creator_id_db_not_found_with_mock(self, mock_connection_pool):
        """Test select_creator_id_db when creator not found."""
        mock_pool, mock_connection, mock_cursor = mock_connection_pool
        mock_cursor.fetchone.return_value = None
        
        result = select_creator_id_db('nonexistent')
        
        assert result is None

    def test_insert_new_creator_db_with_mock(self, mock_connection_pool, sample_creator_data):
        """Test insert_new_creator_db with mocked database."""
        mock_pool, mock_connection, mock_cursor = mock_connection_pool
        mock_cursor.fetchone.return_value = (42,)
        
        result = insert_new_creator_db(
            sample_creator_data['nick'],
            sample_creator_data['display_name'],
            sample_creator_data['profile_image_url'],
            sample_creator_data['twitch_id']
        )
        
        assert result == 42
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()

    def test_select_creators_db_with_mock(self, mock_connection_pool):
        """Test select_creators_db with mocked database."""
        mock_pool, mock_connection, mock_cursor = mock_connection_pool
        mock_cursor.fetchall.return_value = [(1, 'Creator One'), (2, 'Creator Two')]
        
        result = select_creators_db()
        
        assert result == [(1, 'Creator One'), (2, 'Creator Two')]
        mock_cursor.execute.assert_called_once_with("SELECT id, display_name FROM creator")