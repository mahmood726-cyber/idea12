"""Statistical models for network meta-analysis."""

from importlib import import_module

__all__ = ['BayesianNMA', 'FrequentistNMA']

_EXPORTS = {
    'BayesianNMA': ('.bayesian_nma', 'BayesianNMA'),
    'FrequentistNMA': ('.frequentist_nma', 'FrequentistNMA'),
}


def __getattr__(name):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value
