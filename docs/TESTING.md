# Testing

- pytest + pytest-django.
- Tests live next to the code they cover, in each app's `tests.py` or
  `test_*.py` (discovery is set in `pyproject.toml`).
- Shared fixtures live in the project-level `conftest.py` — plain fixtures,
  no factory-boy.
- Every test user needs a distinct email (`<username>@example.com` by
  convention), including ad-hoc `create_user`/`create_superuser` calls.
  `User.email` is unique, so two users left with a blank email collide.
- An autouse `media_root` fixture points `MEDIA_ROOT` at a temporary
  directory, so no test writes to the project's `media/`. File deletions
  run on commit; test them with `django_capture_on_commit_callbacks`.
- Tests never depend on seed data; they build what they need with fixtures
  (testing the seed command itself is fine).
