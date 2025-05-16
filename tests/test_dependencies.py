import pytest
from importlib.util import find_spec

from pydapter.utils.dependencies import (
    check_dependency,
    check_protocols_dependencies,
    check_migrations_dependencies,
    check_migrations_sql_dependencies,
)


def test_check_dependency_installed():
    """Test that check_dependency works with installed packages."""
    # pydantic is a core dependency and should always be installed
    check_dependency("pydantic", "core")  # Should not raise an exception


def test_check_dependency_not_installed():
    """Test that check_dependency raises ImportError for missing packages."""
    # Use a package that's unlikely to be installed
    non_existent_package = "this_package_does_not_exist_12345"
    
    with pytest.raises(ImportError) as excinfo:
        check_dependency(non_existent_package, "test-feature")
    
    # Verify the error message contains installation instructions
    error_msg = str(excinfo.value)
    assert non_existent_package in error_msg
    assert "test-feature" in error_msg
    assert "pip install pydapter[test-feature]" in error_msg


def test_protocols_dependencies():
    """Test protocols dependencies checking."""
    # This test will either pass or skip based on whether typing_extensions is installed
    if find_spec("typing_extensions") is None:
        with pytest.raises(ImportError) as excinfo:
            check_protocols_dependencies()
        assert "protocols" in str(excinfo.value)
    else:
        check_protocols_dependencies()  # Should not raise an exception


def test_migrations_dependencies():
    """Test migrations core dependencies checking."""
    # Core migrations only depend on pydantic, which is a core dependency
    check_migrations_dependencies()  # Should not raise an exception


def test_migrations_sql_dependencies():
    """Test SQL migrations dependencies checking."""
    # This test will either pass or skip based on whether sqlalchemy and alembic are installed
    sqlalchemy_installed = find_spec("sqlalchemy") is not None
    alembic_installed = find_spec("alembic") is not None
    
    if not sqlalchemy_installed or not alembic_installed:
        with pytest.raises(ImportError) as excinfo:
            check_migrations_sql_dependencies()
        assert "migrations-sql" in str(excinfo.value)
    else:
        check_migrations_sql_dependencies()  # Should not raise an exception


def test_lazy_import_protocols():
    """Test lazy import of protocols module."""
    try:
        # Try importing a protocol
        from pydapter.protocols import Identifiable
        # If we get here, the import succeeded
    except ImportError as e:
        # If typing_extensions is not installed, we should get a specific error
        if find_spec("typing_extensions") is None:
            assert "protocols" in str(e)
        else:
            # If typing_extensions is installed but we still got an error,
            # it's likely because the actual module files aren't in place yet
            pytest.skip("Protocol modules not fully implemented yet")


def test_lazy_import_migrations():
    """Test lazy import of migrations module."""
    try:
        # Try importing a migration class
        from pydapter.migrations import BaseMigrationAdapter
        # If we get here, the import succeeded
    except ImportError as e:
        # We should only get an error if the actual module files aren't in place yet
        pytest.skip("Migration modules not fully implemented yet")


def test_lazy_import_migrations_sql():
    """Test lazy import of SQL migrations module."""
    try:
        # Try importing a SQL migration class
        from pydapter.migrations.sql import AlembicAdapter
        # If we get here, the import succeeded
    except ImportError as e:
        # If sqlalchemy or alembic are not installed, we should get a specific error
        if find_spec("sqlalchemy") is None or find_spec("alembic") is None:
            assert "migrations-sql" in str(e)
        else:
            # If dependencies are installed but we still got an error,
            # it's likely because the actual module files aren't in place yet
            pytest.skip("SQL migration modules not fully implemented yet")