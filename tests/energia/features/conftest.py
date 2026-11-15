import pytest

from tests.energia.features.helpers import serie_utc


@pytest.fixture
def serie():
    return serie_utc()
