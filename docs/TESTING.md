# Testing

- pytest + pytest-django.
- Tests live next to the code they cover, in each app's `tests.py` or
  `test_*.py` (discovery is set in `pyproject.toml`).
- Shared fixtures live in the project-level `conftest.py` — plain fixtures,
  no factory-boy.
- Tests never depend on seed data; they build what they need with fixtures
  (testing the seed command itself is fine).
