"""Quality control service for traval operations.

Handles QC ruleset management, validation execution,
and result processing for the traval QC workflow.
"""

import logging
from copy import deepcopy
from functools import partial
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from traval import rulelib

from gwdatalens.app.constants import QCDefaults
from gwdatalens.app.exceptions import TimeSeriesError
from gwdatalens.app.src.data.qc_custom_rules import make_rule_pastas_obswell
from gwdatalens.app.validators import validate_not_empty

logger = logging.getLogger(__name__)


class QCService:
    """Service for quality control operations.

    Encapsulates business logic for:
    - Traval ruleset management
    - Rule parameter derivation
    - QC execution
    - Result formatting

    Parameters
    ----------
    traval_manager : TravalManager
        Traval manager instance
    data_source : PostgreSQLDataSource
        Data source for fetching observations
    """

    def __init__(self, traval_manager, data_source):
        """Initialize with traval manager and data source."""
        self.traval = traval_manager
        self.db = data_source

        self.custom_rules = {"pastas_obswell": make_rule_pastas_obswell(self.db)}

    def get_rule_from_ruleset(
        self, istep: Optional[int] = None, stepname: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get rule from current ruleset.

        Parameters
        ----------
        istep : int, optional
            Rule step index
        stepname : str, optional
            Rule name

        Returns
        -------
        dict
            Rule configuration
        """
        if istep is not None:
            return self.traval._ruleset.get_rule(istep=istep)
        elif stepname is not None:
            return self.traval._ruleset.get_rule(stepname=stepname)
        else:
            raise ValueError("Must provide istep or stepname")

    def update_rule_parameter(
        self, rule_name: str, param_name: str, param_value: Any
    ) -> None:
        """Update a single rule parameter.

        Parameters
        ----------
        rule_name : str
            Name of the rule to update
        param_name : str
            Parameter name
        param_value : Any
            New parameter value
        """
        try:
            ruledict = self.traval._ruleset.get_rule(stepname=rule_name)
            ruledict["kwargs"][param_name] = param_value
            self.traval._ruleset.update_rule(**ruledict)
        except KeyError:
            logger.error("Rule %s or parameter %s not found", rule_name, param_name)
            raise
        # backup for other exceptions
        except Exception as e:
            logger.error("Failed to update rule %s.%s: %s", rule_name, param_name, e)
            raise

    def add_rule_to_ruleset(
        self,
        rule_name: str,
        rule_kwargs: Optional[Dict[str, Any]] = None,
        inject_manual_obs: bool = True,
    ) -> Dict[str, Any]:
        """Add a new rule to the current ruleset.

        Parameters
        ----------
        rule_name : str
            Name of the rule function from rulelib
        rule_kwargs : dict, optional
            Rule parameters
        inject_manual_obs : bool
            Whether to inject manual observation fetcher

        Returns
        -------
        dict
            Added rule configuration
        """
        try:
            if rule_name in self.custom_rules:
                func = self.custom_rules[rule_name]
            else:
                func = getattr(rulelib, rule_name)

            if rule_kwargs is None:
                rule_kwargs = self._generate_default_kwargs(func)

            # Inject manual observation fetcher if needed
            if inject_manual_obs and "manual_obs" in func.__code__.co_varnames:
                rule_kwargs["manual_obs"] = partial(
                    self.db.get_timeseries,
                    observation_type="controlemeting",
                    column=self.db.value_column,
                )

            rule = {"name": rule_name, "func": func, "kwargs": rule_kwargs}

            # Add to ruleset
            nrules = len(self.traval._ruleset.rules)
            if nrules > 1:
                # Remove combine_results if present
                try:
                    self.traval._ruleset.del_rule("combine_results")
                except KeyError:
                    pass

                # Add new rule
                self.traval._ruleset.add_rule(
                    rule_name, func, apply_to=0, kwargs=rule_kwargs
                )

                # Re-add combine_results
                self.traval._ruleset.add_rule(
                    "combine_results",
                    rulelib.rule_combine_nan_or,
                    apply_to=tuple(range(1, nrules + 1)),
                )
            else:
                self.traval._ruleset.add_rule(
                    rule_name, func, apply_to=0, kwargs=rule_kwargs
                )

            return rule
        except AttributeError as e:
            logger.error("Rule %s not found in rulelib: %s", rule_name, e)
            raise
        # backup for other exceptions
        except Exception as e:
            logger.error("Failed to add rule %s: %s", rule_name, e)
            raise

    def delete_rule_from_ruleset(self, rule_identifier: str) -> None:
        """Delete a rule from the ruleset.

        Parameters
        ----------
        rule_identifier : str
            Rule step identifier (e.g., "0-rule_name")
        """
        try:
            rule_index = rule_identifier.split("-")[0]
            self.traval._ruleset.del_rule(rule_index)

            # Update combine_results
            remaining_rules = len(self.traval._ruleset.rules) - 1
            if remaining_rules > 1:
                try:
                    self.traval._ruleset.del_rule("combine_results")
                except KeyError:
                    pass

                self.traval._ruleset.add_rule(
                    "combine_results",
                    rulelib.rule_combine_nan_or,
                    apply_to=tuple(range(1, remaining_rules + 1)),
                )
            else:
                try:
                    self.traval._ruleset.del_rule("combine_results")
                except KeyError:
                    pass
        except KeyError as e:
            logger.error("Failed to delete rule %s: %s", rule_identifier, e)
            raise

    def reset_ruleset_to_default(self) -> None:
        """Reset ruleset to original default configuration."""
        self.traval._ruleset = deepcopy(self.traval.ruleset)

    def derive_rule_parameters_for_series(
        self, series_name: str
    ) -> Tuple[List[Any], List[str]]:
        """Derive rule parameters for a specific time series.

        Evaluates callable parameters with the series name.

        Parameters
        ----------
        series_name : str
            Time series name

        Returns
        -------
        tuple
            (derived_values, errors) lists
        """
        values = []
        errors = []

        nrules = len(self.traval._ruleset.rules) - 1
        for i in range(1, nrules + 1):
            irule = self.traval._ruleset.get_rule(istep=i)
            irule_orig = self.traval.ruleset.get_rule(istep=i)

            for (k, v), (_, vorig) in zip(
                irule["kwargs"].items(), irule_orig["kwargs"].items(), strict=False
            ):
                if callable(vorig):
                    try:
                        v = vorig(series_name)
                    except KeyError as e:
                        msg = f"{irule['name']}.{k}: {e}"
                        logger.error(
                            "Could not find parameter for rule %s.%s series %s",
                            irule["name"],
                            k,
                            series_name,
                        )
                        errors.append(msg)
                    # generic exception to catch other errors in user-defined callables
                    except Exception as e:
                        logger.error(
                            "Could not derive parameter for rule %s.%s, series %s",
                            irule["name"],
                            k,
                            series_name,
                        )
                        errors.append(f"{irule['name']}.{k}: {e}")

                values.append(v)

        return values, errors

    def run_qc_on_series(
        self,
        wid: int,
        tmin: Optional[pd.Timestamp] = None,
        tmax: Optional[pd.Timestamp] = None,
        only_unvalidated: bool = False,
    ) -> Tuple[pd.Series, pd.DataFrame]:
        """Run quality control on a time series.

        Parameters
        ----------
        wid : int
            Well internal ID
        tmin : pd.Timestamp, optional
            Start time filter
        tmax : pd.Timestamp, optional
            End time filter
        only_unvalidated : bool
            Whether to only process unvalidated observations

        Returns
        -------
        tuple
            (series, result_dataframe)
        """
        try:
            # Get the series
            series = self.db.get_timeseries(wid=wid, column=self.db.value_column)
            validate_not_empty(series, context=f"time series for well {wid}")

            # Apply time filters
            if tmin is not None:
                series = series.loc[tmin:]
            if tmax is not None:
                series = series.loc[:tmax]

            # Run traval
            result = self.traval._ruleset.apply(series)

            return series, result
        except TimeSeriesError:
            logger.exception("Failed to get time series %s", wid)
            raise
        except TypeError:
            logger.exception("Error in applying ruleset to series %s", wid)
        except Exception as e:
            logger.exception("Failed to run QC on series %s: %s", wid, e)
            raise

    def run_traval(
        self,
        wid: int,
        tmin: Optional[pd.Timestamp] = None,
        tmax: Optional[pd.Timestamp] = None,
        only_unvalidated: bool = False,
    ):
        """Run traval via the traval manager."""
        return self.traval.run_traval(
            wid,
            tmin=tmin,
            tmax=tmax,
            only_unvalidated=only_unvalidated,
        )

    def get_resolved_ruleset_for_series(self, series_name: str):
        """Get resolved ruleset with parameters evaluated for series.

        Parameters
        ----------
        series_name : str
            Time series name

        Returns
        -------
        RuleSet
            Resolved ruleset
        """
        return self.traval._ruleset.get_resolved_ruleset(series_name)

    def _generate_default_kwargs(self, func) -> Dict[str, Any]:
        """Generate default kwargs for a rule function.

        Parameters
        ----------
        func : callable
            Rule function

        Returns
        -------
        dict
            Default parameter values
        """
        import inspect

        sig = inspect.signature(func)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param_name in ("series", "manual_obs"):
                continue
            if param.default is not inspect.Parameter.empty:
                kwargs[param_name] = param.default
            else:
                # Provide sensible defaults based on common parameter names
                if "threshold" in param_name.lower():
                    kwargs[param_name] = QCDefaults.THRESHOLD
                elif "window" in param_name.lower():
                    kwargs[param_name] = QCDefaults.WINDOW_SIZE
                else:
                    kwargs[param_name] = None

        return kwargs
