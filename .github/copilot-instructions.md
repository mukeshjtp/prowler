# Prowler - Open Cloud Security Platform

Prowler is an open-source security tool for AWS, Azure, Google Cloud, Kubernetes, Microsoft 365, and GitHub. It contains hundreds of built-in controls for compliance frameworks like CIS, NIST, PCI-DSS, GDPR, and more.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Environment Setup
- Python 3.9.1 to 3.13 supported (tested with 3.12.3)
- Install Poetry for dependency management: `pip3 install poetry`
- Clone repository: `git clone https://github.com/prowler-cloud/prowler`
- Install dependencies: `poetry install` -- takes ~1.5 minutes. NEVER CANCEL.
- Activate environment: `eval "$(poetry env activate)"`

### Development and Testing
- **CRITICAL: Test suite has 5,984 tests and takes 28+ minutes minimum. NEVER CANCEL. Set timeout to 60+ minutes.**
- Run tests: `make test` -- **NEVER CANCEL: Takes 28+ minutes minimum. Use timeout of 60+ minutes.**
- Run linting: `make lint` -- takes ~1 minute. Includes flake8, black, and pylint
- Format code: `make format` -- runs black code formatter, takes ~30 seconds
- Check version: `python prowler-cli.py -v` or `prowler -v`

### Key Commands
- Basic help: `prowler --help`
- List providers: `prowler aws --help`, `prowler azure --help`, etc.
- Run AWS scan: `prowler aws` (requires AWS credentials)
- Run dashboard: `prowler dashboard`

## Repository Structure

### Core Components
```
prowler/                 # Main Python package
├── __main__.py         # CLI entry point
├── providers/          # Cloud provider implementations
├── compliance/         # Compliance frameworks
├── config/            # Configuration management
└── lib/               # Shared libraries

tests/                  # Test suite (5,984 tests)
api/                    # Django REST API backend
ui/                     # Next.js frontend
dashboard/              # Local dashboard component
```

### Key Files
- `prowler-cli.py` -- Main CLI entry point
- `pyproject.toml` -- Poetry configuration and dependencies
- `Makefile` -- Development commands
- `docker-compose.yml` -- Full Prowler App stack

## Validation Requirements

### Always Test Changes
- **MANDATORY: Run `make test` after any changes** -- NEVER CANCEL, takes 20+ minutes
- **MANDATORY: Run `make lint` before committing** -- pre-commit will fail otherwise
- Test CLI functionality: `prowler --help` and `prowler -v`

### Manual Testing Scenarios
After making changes, always test:
1. **CLI Functionality**: `prowler aws --help` (should show AWS-specific options)
2. **Version Check**: `prowler -v` (should show current version)
3. **Basic Scan**: `prowler aws --list-checks` (if AWS credentials available)
4. **Dashboard**: `prowler dashboard` (should start local web server)

## Prowler App (Full Stack)

### API Component
- Location: `api/` directory
- Technology: Django REST Framework
- Setup:
  ```bash
  cd api
  poetry install
  eval "$(poetry env activate)"
  set -a && source .env
  docker compose up postgres valkey -d
  cd src/backend
  python manage.py migrate --database admin
  gunicorn -c config/guniconf.py config.wsgi:application
  ```
- Access: http://localhost:8080/api/v1/docs

### UI Component  
- Location: `ui/` directory
- Technology: Next.js
- Setup:
  ```bash
  cd ui
  npm install
  npm run build
  npm start
  ```
- Access: http://localhost:3000

### Docker Compose (Recommended)
- Quick setup: `docker compose up -d`
- Includes: API, UI, PostgreSQL, Valkey (Redis)
- Access: http://localhost:3000

## Common Issues and Solutions

### Build/Test Issues
- **Poetry not found**: Install with `pip3 install poetry`
- **Tests timing out**: NEVER CANCEL - they take 20+ minutes minimum
- **Pre-commit failures**: Run `make lint` and `make format` first
- **Docker architecture issues**: Set `DOCKER_DEFAULT_PLATFORM=linux/amd64`

### Cloud Provider Setup
- AWS: Configure credentials via AWS CLI or environment variables
- Azure: Use `az login` or service principal
- GCP: Set up service account and GOOGLE_APPLICATION_CREDENTIALS

## Critical Timing Information

**NEVER CANCEL these operations:**
- `poetry install`: ~1.5 minutes
- `make test`: **20+ minutes minimum** (5,984 tests) - Set timeout to 45+ minutes
- `make lint`: ~2-3 minutes  
- `npm install` (UI): ~2-3 minutes
- `npm run build` (UI): ~3-5 minutes
- Docker compose up: ~2-3 minutes for container startup

## Development Workflow

1. **Setup**: Install Poetry, run `poetry install`, activate environment
2. **Make Changes**: Edit code in `prowler/` directory
3. **Test Immediately**: Run `make test` -- NEVER CANCEL, takes 20+ minutes
4. **Lint**: Run `make lint` before committing
5. **Validate**: Test CLI commands manually
6. **Commit**: Pre-commit hooks will run additional checks

## Available Providers and Checks

| Provider | Checks | Services | Frameworks |
|----------|---------|----------|------------|
| AWS | 567 | 82 | 36 |
| Azure | 142 | 18 | 10 |
| GCP | 79 | 13 | 10 |
| Kubernetes | 83 | 7 | 5 |
| M365 | 69 | 7 | 3 |
| GitHub | 16 | 2 | 1 |

Use `prowler <provider> --list-checks` to see all available checks for a provider.