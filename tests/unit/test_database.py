"""Tests for the unified CinchDB interface."""

import pytest
from unittest.mock import Mock, patch, PropertyMock

from cinchdb.core.database import CinchDB, connect, connect_api
from cinchdb.models import Column


class TestCinchDB:
    """Test the CinchDB class."""

    def test_local_connection_init(self, tmp_path):
        """Test initializing a local connection."""
        db = CinchDB(
            database="test_db", branch="main", tenant="main", project_dir=tmp_path
        )

        assert db.database == "test_db"
        assert db.branch == "main"
        assert db.tenant == "main"
        assert db.project_dir == tmp_path
        assert db.is_local is True
        assert db.api_url is None
        assert db.api_key is None

    def test_remote_connection_init(self):
        """Test initializing a remote connection."""
        db = CinchDB(
            database="test_db",
            branch="dev",
            tenant="customer1",
            api_url="https://api.example.com",
            api_key="test-key",
        )

        assert db.database == "test_db"
        assert db.branch == "dev"
        assert db.tenant == "customer1"
        assert db.project_dir is None
        assert db.is_local is False
        assert db.api_url == "https://api.example.com"
        assert db.api_key == "test-key"

    def test_init_requires_connection_params(self):
        """Test that init requires either local or remote params."""
        with pytest.raises(ValueError, match="Must provide either project_dir"):
            CinchDB(database="test_db")

    def test_local_managers_lazy_load(self, tmp_path):
        """Test that local managers are lazy loaded."""
        db = CinchDB(database="test_db", project_dir=tmp_path)

        # Managers should not be loaded yet
        assert db._table_manager is None
        assert db._column_manager is None
        assert db._query_manager is None

        # Access a manager
        with patch("cinchdb.managers.table.TableManager") as mock_table_manager:
            _ = db.tables
            mock_table_manager.assert_called_once_with(
                tmp_path, "test_db", "main", "main"
            )

        # Should be cached
        with patch("cinchdb.managers.table.TableManager") as mock_table_manager:
            _ = db.tables
            mock_table_manager.assert_not_called()

    def test_remote_managers_raise_error(self):
        """Test that accessing managers on remote connection raises error."""
        db = CinchDB(
            database="test_db", api_url="https://api.example.com", api_key="test-key"
        )

        with pytest.raises(RuntimeError, match="Direct manager access not available"):
            _ = db.tables

        with pytest.raises(RuntimeError, match="Direct manager access not available"):
            _ = db.columns

    def test_local_query(self, tmp_path):
        """Test query execution on local connection."""
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.query.QueryManager") as mock_query_manager:
            mock_instance = Mock()
            mock_instance.execute.return_value = [{"id": 1, "name": "test"}]
            mock_query_manager.return_value = mock_instance

            result = db.query("SELECT * FROM users WHERE id = ?", [1])

            mock_query_manager.assert_called_once_with(
                tmp_path, "test_db", "main", "main"
            )
            mock_instance.execute.assert_called_once_with(
                "SELECT * FROM users WHERE id = ?", [1]
            )
            assert result == [{"id": 1, "name": "test"}]

    def test_remote_query(self):
        """Test query execution on remote connection."""
        # Create a mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": 1, "name": "test"}]}
        mock_session.request.return_value = mock_response

        # Patch the session property to return our mock
        with patch.object(
            CinchDB, "session", new_callable=PropertyMock
        ) as mock_session_prop:
            mock_session_prop.return_value = mock_session

            db = CinchDB(
                database="test_db",
                api_url="https://api.example.com",
                api_key="test-key",
            )

            result = db.query("SELECT * FROM users")

            mock_session.request.assert_called_once_with(
                "POST",
                "https://api.example.com/query",
                params={"database": "test_db", "branch": "main", "tenant": "main"},
                json={"sql": "SELECT * FROM users"},
            )
            assert result == [{"id": 1, "name": "test"}]

    def test_local_create_table(self, tmp_path):
        """Test table creation on local connection."""
        db = CinchDB(database="test_db", project_dir=tmp_path)

        columns = [Column(name="name", type="TEXT"), Column(name="age", type="INTEGER")]

        with patch("cinchdb.managers.table.TableManager") as mock_table_manager:
            mock_instance = Mock()
            mock_table_manager.return_value = mock_instance

            db.create_table("users", columns)

            mock_instance.create_table.assert_called_once_with("users", columns)

    def test_remote_create_table(self):
        """Test table creation on remote connection."""
        # Create a mock session
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_session.request.return_value = mock_response

        # Patch the session property to return our mock
        with patch.object(
            CinchDB, "session", new_callable=PropertyMock
        ) as mock_session_prop:
            mock_session_prop.return_value = mock_session

            db = CinchDB(
                database="test_db",
                api_url="https://api.example.com",
                api_key="test-key",
            )

            columns = [
                Column(name="name", type="TEXT", nullable=False),
                Column(name="age", type="INTEGER", nullable=True),
            ]

            db.create_table("users", columns)

            mock_session.request.assert_called_once_with(
                "POST",
                "https://api.example.com/tables",
                params={"database": "test_db", "branch": "main"},
                json={
                    "name": "users",
                    "columns": [
                        {"name": "name", "type": "TEXT", "nullable": False},
                        {"name": "age", "type": "INTEGER", "nullable": True},
                    ],
                },
            )

    def test_local_insert(self, tmp_path):
        """Test insert on local connection."""
        db = CinchDB(database="test_db", project_dir=tmp_path)
        
        with patch("cinchdb.managers.data.DataManager") as mock_data_manager:
            mock_instance = Mock()
            mock_instance.create_from_dict.return_value = {
                "id": "generated-id",
                "name": "Test User",
                "email": "test@example.com",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
            mock_data_manager.return_value = mock_instance
            
            result = db.insert("users", {"name": "Test User", "email": "test@example.com"})
            
            mock_data_manager.assert_called_once_with(
                tmp_path, "test_db", "main", "main"
            )
            mock_instance.create_from_dict.assert_called_once_with(
                "users", {"name": "Test User", "email": "test@example.com"}
            )
            assert result["id"] == "generated-id"
            assert result["name"] == "Test User"
    
    def test_remote_insert(self):
        """Test insert on remote connection."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "remote-id",
            "name": "Remote User",
            "created_at": "2024-01-01T00:00:00"
        }
        mock_session.request.return_value = mock_response
        
        with patch.object(CinchDB, "session", new_callable=PropertyMock) as mock_session_prop:
            mock_session_prop.return_value = mock_session
            
            db = CinchDB(
                database="test_db",
                api_url="https://api.example.com",
                api_key="test-key"
            )
            
            result = db.insert("users", {"name": "Remote User"})
            
            mock_session.request.assert_called_once_with(
                "POST",
                "https://api.example.com/tables/users/data",
                params={"database": "test_db", "branch": "main", "tenant": "main"},
                json={"data": {"name": "Remote User"}}
            )
            assert result["id"] == "remote-id"
            assert result["name"] == "Remote User"

    def test_context_manager(self):
        """Test context manager functionality."""
        # Create a mock session
        mock_session = Mock()

        with patch.object(
            CinchDB, "session", new_callable=PropertyMock
        ) as mock_session_prop:
            mock_session_prop.return_value = mock_session

            with CinchDB(
                database="test_db",
                api_url="https://api.example.com",
                api_key="test-key",
            ) as db:
                # Force session creation
                _ = db.session
                # Mark that we have a session
                db._session = mock_session

            # Session should be closed
            mock_session.close.assert_called_once()

    def test_local_list_changes(self, tmp_path):
        """Test list_changes on local connection."""
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.change_tracker.ChangeTracker") as mock_tracker:
            from cinchdb.models import Change, ChangeType
            from datetime import datetime, timezone

            # Mock changes
            mock_changes = [
                Change(
                    id="change-1",
                    type=ChangeType.CREATE_TABLE,
                    entity_type="table",
                    entity_name="users",
                    branch="main",
                    applied=True,
                    created_at=datetime.now(timezone.utc),
                ),
                Change(
                    id="change-2",
                    type=ChangeType.ADD_COLUMN,
                    entity_type="table",
                    entity_name="users",
                    branch="main",
                    applied=False,
                    created_at=datetime.now(timezone.utc),
                ),
            ]

            mock_instance = Mock()
            mock_instance.get_changes.return_value = mock_changes
            mock_tracker.return_value = mock_instance

            result = db.list_changes()

            mock_tracker.assert_called_once_with(tmp_path, "test_db", "main")
            mock_instance.get_changes.assert_called_once()
            assert len(result) == 2
            assert result[0].id == "change-1"
            assert result[0].type == ChangeType.CREATE_TABLE
            assert result[1].id == "change-2"
            assert result[1].applied is False

    def test_remote_list_changes(self):
        """Test list_changes on remote connection."""
        db = CinchDB(
            database="test_db",
            branch="dev",
            api_url="https://api.example.com",
            api_key="test-key",
        )

        with patch.object(db, "_make_request") as mock_request:
            from datetime import datetime

            # Mock API response
            mock_request.return_value = {
                "changes": [
                    {
                        "id": "change-1",
                        "type": "create_table",
                        "entity_type": "table",
                        "entity_name": "users",
                        "branch": "dev",
                        "applied": True,
                        "created_at": "2024-01-01T12:00:00",
                        "updated_at": None,
                        "details": {},
                        "sql": "CREATE TABLE users (...)",
                    },
                    {
                        "id": "change-2",
                        "type": "add_column",
                        "entity_type": "table",
                        "entity_name": "users",
                        "branch": "dev",
                        "applied": False,
                        "created_at": "2024-01-02T12:00:00",
                        "updated_at": "2024-01-02T13:00:00",
                        "details": {"column_name": "email"},
                        "sql": "ALTER TABLE users ADD COLUMN email TEXT",
                    },
                ]
            }

            result = db.list_changes()

            mock_request.assert_called_once_with("GET", "/branches/dev/changes")
            assert len(result) == 2
            assert result[0].id == "change-1"
            assert result[0].type == "create_table"
            assert result[0].applied is True
            assert isinstance(result[0].created_at, datetime)
            assert result[1].id == "change-2"
            assert result[1].type == "add_column"
            assert result[1].applied is False
            assert isinstance(result[1].updated_at, datetime)


class TestFactoryFunctions:
    """Test the factory functions."""

    @patch("cinchdb.config.Config")
    def test_connect_with_project_dir(self, mock_config, tmp_path):
        """Test connect function with explicit project dir."""
        db = connect("test_db", "dev", "tenant1", project_dir=tmp_path)

        assert db.database == "test_db"
        assert db.branch == "dev"
        assert db.tenant == "tenant1"
        assert db.project_dir == tmp_path
        assert db.is_local is True

        # Config should not be used
        mock_config.find_project_root.assert_not_called()

    @patch("cinchdb.core.database.get_project_root")
    def test_connect_find_project_root(self, mock_get_project_root, tmp_path):
        """Test connect function finding project root."""
        mock_get_project_root.return_value = tmp_path

        db = connect("test_db")

        assert db.database == "test_db"
        assert db.branch == "main"
        assert db.tenant == "main"
        assert db.project_dir == tmp_path
        assert db.is_local is True

        mock_get_project_root.assert_called_once()

    @patch("cinchdb.core.database.get_project_root")
    def test_connect_no_project_found(self, mock_get_project_root):
        """Test connect function when no project found."""
        mock_get_project_root.side_effect = FileNotFoundError(
            "No .cinchdb directory found"
        )

        with pytest.raises(ValueError, match="No .cinchdb directory found"):
            connect("test_db")

    def test_connect_api(self):
        """Test connect_api function."""
        db = connect_api(
            "https://api.example.com", "test-key", "test_db", "dev", "tenant1"
        )

        assert db.database == "test_db"
        assert db.branch == "dev"
        assert db.tenant == "tenant1"
        assert db.api_url == "https://api.example.com"
        assert db.api_key == "test-key"
        assert db.is_local is False
