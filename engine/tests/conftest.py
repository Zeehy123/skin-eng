# the test configuration file for pytest. It defines fixtures that can be used in tests.

from pathlib import Path
import pytest

from skin_engine.snapshot import Snapshot

SEED = Path(__file__).resolve().parents[2] / "seed" / "skincare_seed_v1.json"
# .resolve() This converts the path into an absolute path.
# parents allows you to navigate upward through the directory structure.

@pytest.fixture(scope="session")
# prepares what the test needs to run. The scope="session" means that the fixture is created once per test session.
def snapshot():
  # returns a Snapshot object that is created from the JSON file located at the SEED path.
  return Snapshot.from_file(SEED)


@pytest.fixture(scope="session")
def cases(snapshot):
  return {case["name"][0]: case for case in snapshot.data["test_cases"]}