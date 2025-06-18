import dagster as dg
import pytest


@pytest.fixture(scope="function")
def instance() -> dg.DagsterInstance:
    return dg.DagsterInstance.ephemeral()
