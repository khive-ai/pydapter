from importlib.util import find_spec


def check_dependency(package_name: str, feature_name: str) -> None:
    """
    Check if an optional dependency is installed.

    Args:
        package_name: The name of the package to check for
        feature_name: The name of the feature requiring this package

    Raises:
        ImportError: If the package is not installed
    """
    if find_spec(package_name) is None:
        raise ImportError(
            f"The '{feature_name}' feature requires the '{package_name}' package. "
            f"Install it with: pip install pydapter[{feature_name}]"
        )


def check_migrations_dependencies() -> None:
    """Check if core migrations dependencies are installed."""
    pass  # Core migrations only depend on pydantic, which is already a dependency


def check_migrations_sql_dependencies() -> None:
    """Check if SQL migrations dependencies are installed."""
    check_dependency("sqlalchemy", "migrations-sql")
    check_dependency("alembic", "migrations-sql")
