"""Packaging smoke check; no models, containers, or evaluation runs."""
from importlib.metadata import version
import capability_eval


def test_installed_package_version():
    assert version("capability-eval-lab") == capability_eval.__version__
