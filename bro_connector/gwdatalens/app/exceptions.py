"""Custom exception hierarchy for gwdatalens.

Provides specific exception types for different error scenarios,
replacing generic Exception handling throughout the codebase.
"""


class DataAccessError(Exception):
    """Raised when database or data source access fails."""

    pass


class NotFoundError(DataAccessError):
    """Raised when expected data is not found."""

    pass


class ValidationError(Exception):
    """Raised when data validation fails."""

    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass


class QueryError(DataAccessError):
    """Raised when a query returns unexpected results."""

    pass


class MultipleResultsError(QueryError):
    """Raised when a query expecting one result returns multiple."""

    pass


class EmptyResultError(QueryError):
    """Raised when a query returns no results."""

    pass


class DataQualityError(ValidationError):
    """Raised when data quality checks fail."""

    pass


class TimeSeriesError(DataAccessError):
    """Raised when time series operations fail."""

    pass


class QCError(Exception):
    """Raised when quality control operations fail."""

    pass
