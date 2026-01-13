"""Validation functions for common checks across the application.

Extracts repeated validation patterns into reusable functions.
"""

import logging
from typing import Any, List, Optional, Union

import pandas as pd

from gwdatalens.app.exceptions import (
    EmptyResultError,
    MultipleResultsError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def validate_single_result(
    query_result: Union[pd.DataFrame, pd.Series], context: str = "query"
) -> Any:
    """Validate that a query returned exactly one result.

    Parameters
    ----------
    query_result : DataFrame or Series
        Query result to validate
    context : str
        Context for error messages (e.g., "well lookup")

    Returns
    -------
    First row/item of result

    Raises
    ------
    EmptyResultError
        If result is empty
    MultipleResultsError
        If result has multiple items
    """
    if isinstance(query_result, pd.DataFrame):
        if query_result.empty:
            raise EmptyResultError(f"No results found for {context}")
        if len(query_result) > 1:
            raise MultipleResultsError(
                f"Expected one result for {context}, got {len(query_result)}"
            )
        return query_result.iloc[0]
    elif isinstance(query_result, pd.Series):
        if query_result.empty:
            raise EmptyResultError(f"No results found for {context}")
        return (
            query_result.iloc[0]
            if isinstance(query_result.iloc[0], (int, float))
            else query_result.iloc[0]
        )
    else:
        raise ValidationError(f"Expected DataFrame or Series, got {type(query_result)}")


def validate_not_empty(
    df: Union[pd.DataFrame, pd.Series, List],
    context: str = "data",
) -> Union[pd.DataFrame, pd.Series]:
    """Validate that a DataFrame/Series is not empty.

    Parameters
    ----------
    df : DataFrame or Series
        Data to validate
    context : str
        Context for error messages

    Returns
    -------
    The input df if valid

    Raises
    ------
    EmptyResultError
        If data is empty
    """
    if isinstance(df, list) and len(df) == 0:
        raise EmptyResultError(f"No {context} available")
    elif isinstance(df, (pd.Series, pd.DataFrame)) and df.empty:
        raise EmptyResultError(f"No {context} available")
    return df


def validate_not_none(value: Any, context: str = "value") -> Any:
    """Validate that a value is not None.

    Parameters
    ----------
    value : Any
        Value to validate
    context : str
        Context for error messages

    Returns
    -------
    The input value if not None

    Raises
    ------
    ValidationError
        If value is None
    """
    if value is None:
        raise ValidationError(f"{context.capitalize()} cannot be None")
    return value


def validate_selection_limit(
    items: Union[List, pd.Series],
    limit: int,
) -> bool:
    """Check if selection exceeds limit.

    Parameters
    ----------
    items : list or Series
        Items to validate
    limit : int
        Maximum allowed items

    Returns
    -------
    bool
        True if limit exceeded, False otherwise
    """
    count = len(items) if hasattr(items, "__len__") else len(items.tolist())
    return count > limit


def validate_is_numeric(value: Any, context: str = "value") -> float:
    """Validate that value is numeric and return as float.

    Parameters
    ----------
    value : Any
        Value to validate
    context : str
        Context for error messages

    Returns
    -------
    float
        Value as float

    Raises
    ------
    ValidationError
        If value is not numeric or None
    """
    if value is None:
        raise ValidationError(f"{context} cannot be None")
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"{context} must be numeric, got {value}") from e


def validate_date_range(tmin, tmax, context: str = "date range") -> tuple:
    """Validate date range is valid.

    Parameters
    ----------
    tmin : datetime-like
        Start date
    tmax : datetime-like
        End date
    context : str
        Context for error messages

    Returns
    -------
    tuple
        (tmin, tmax) as Timestamps if valid

    Raises
    ------
    ValidationError
        If range is invalid
    """
    if pd.isna(tmin) or pd.isna(tmax):
        raise ValidationError(f"{context} contains NaT")

    tmin = pd.Timestamp(tmin)
    tmax = pd.Timestamp(tmax)

    if tmin >= tmax:
        raise ValidationError(f"{context} start date must be before end date")

    return tmin, tmax


def validate_well_id(wid: Optional[int], context: str = "well") -> int:
    """Validate well ID is not None.

    Parameters
    ----------
    wid : int or None
        Well ID to validate
    context : str
        Context for error messages

    Returns
    -------
    int
        The validated well ID

    Raises
    ------
    ValidationError
        If well ID is None
    """
    if wid is None:
        raise ValidationError(f"No {context} selected")
    return wid
