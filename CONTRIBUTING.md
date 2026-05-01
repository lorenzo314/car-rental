# Contributing

## Development workflow

```bash
# 1. Create a branch from develop
git checkout develop
git pull
git checkout -b feat/your-feature-name

# 2. Make changes, run checks locally before pushing
ruff check .
black --check .
mypy app/
pytest

# 3. Commit using conventional commits (see below)
git add .
git commit -m "feat(vehicles): add fuel level validation"

# 4. Push and open a pull request against develop
git push origin feat/your-feature-name
```

CI runs automatically on every push and pull request.
A pull request cannot be merged if CI is red.

---

## Conventional commits

Every commit message must follow the
[Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

### Types

| Type | When to use |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `style` | Formatting, whitespace — no logic change |
| `refactor` | Code restructuring — no feature or bug fix |
| `test` | Adding or fixing tests |
| `chore` | Tooling, dependencies, config — no production code |
| `perf` | Performance improvement |
| `ci` | Changes to CI/CD configuration |
| `db` | Schema or migration changes |

### Scopes

Use the module or layer being changed:

`vehicles` · `clients` · `rentals` · `reservations` · `blacklist`
`api` · `ui` · `services` · `models` · `migrations` · `seeds`
`config` · `auth` · `email` · `ci` · `deps`

### Examples

```
feat(rentals): add walk-in rental without prior reservation

fix(vehicles): prevent duplicate licence plate on update

docs(readme): add getting started section

test(factories): add edge cases for rental_event_payload

chore(deps): upgrade sqlalchemy to 2.0.30

db(migrations): add email_consent column to client

ci: add coverage upload step to workflow

refactor(services): extract blacklist check into helper function
```

### Breaking changes

Add `!` after the type and a `BREAKING CHANGE:` footer:

```
feat(api)!: rename /rentals endpoint to /rental-archive

BREAKING CHANGE: clients of the API must update their base URL.
```

---

## Branch naming

| Pattern | Purpose |
|---|---|
| `feat/<description>` | New feature |
| `fix/<description>` | Bug fix |
| `docs/<description>` | Documentation |
| `refactor/<description>` | Refactoring |
| `test/<description>` | Tests only |
| `chore/<description>` | Tooling / config |
| `db/<description>` | Schema or migration |

---

## First-time setup reminder

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your local credentials
alembic upgrade head
python db/seeds/seed.py
```
