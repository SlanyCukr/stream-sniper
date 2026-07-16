# GitHub Actions CI/CD Workflows

This document describes the GitHub Actions workflows implemented for the Stream Sniper project.

## Overview

The CI/CD pipeline consists of four main workflows:

1. **CI Pipeline** (`ci.yml`) - Code quality, testing, and package validation
2. **Docker Build & Publish** (`docker.yml`) - Container image build and registry publishing
3. **Security Scanning** (`security.yml`) - Comprehensive security analysis
4. **Release** (`release.yml`) - Automated versioning and package publishing

## Workflows Detail

### 1. CI Pipeline (`ci.yml`)

**Triggers:**
- Push to `main` and `develop` branches
- Pull requests to `main` and `develop` branches
- Manual dispatch

**Jobs:**

#### `lint` - Code Quality & Linting
- Runs on Ubuntu with Python 3.14
- Code formatting check with Black
- Import sorting check with isort
- Linting with flake8
- Type checking with mypy

#### `test` - Tests (Python 3.14)
- Matrix strategy testing multiple Python versions
- PostgreSQL service container for integration tests
- Unit and integration test execution
- Code coverage reporting with Codecov

#### `package-test` - Package Installation Test
- Validates package can be built and installed
- Tests CLI commands are available
- Verifies module imports work correctly

#### `docker-test` - Docker Build Test
- Builds both API and Collector Docker images
- Validates images can run and show help
- Uses build cache for efficiency

#### `security-baseline` - Security Baseline Check
- Dependency vulnerability scanning with Safety
- Security linting with Bandit
- Security pattern detection with Semgrep

#### `frontend` - Frontend Build & Browser Confidence
- Installs the locked Node dependencies on Node.js 22
- Runs TypeScript and the incremental checked-JavaScript boundary gate
- Enforces the ratcheted Vitest coverage baseline
- Installs Playwright Chromium and runs the critical browser smoke journeys
- Builds the Next.js standalone production output

### 2. Docker Build & Publish (`docker.yml`)

**Triggers:**
- Push to `main` branch
- Git tags starting with `v*`
- Pull requests to `main` branch
- Manual dispatch

**Jobs:**

#### `build-and-push` - Build and Push Docker Images
- Matrix strategy for API and Collector images
- Multi-platform builds (linux/amd64, linux/arm64)
- Publishes to GitHub Container Registry
- Automatic tagging based on git refs

#### `security-scan` - Security Scan Docker Images
- Trivy vulnerability scanning
- SARIF results uploaded to GitHub Security tab
- Runs only on push events (not PRs)

#### `docker-compose-test` - Docker Compose Integration Test
- Tests docker-compose configuration
- Validates service startup and health
- Integration testing between components

### 3. Security Scanning (`security.yml`)

**Triggers:**
- Push to `main` and `develop` branches
- Pull requests to `main` and `develop` branches
- Weekly schedule (Sundays at 2 AM UTC)
- Manual dispatch

**Jobs:**

#### `dependency-check` - Dependency Vulnerability Scan
- Safety (PyUp.io) vulnerability database
- pip-audit for Python package vulnerabilities
- JSON reports uploaded as artifacts

#### `code-security` - Code Security Analysis
- Bandit for Python security issues
- Semgrep for security patterns
- Report artifacts with 30-day retention

#### `codeql` - CodeQL Analysis
- GitHub's semantic code analysis
- Security-focused query suites
- Results integrated with GitHub Security tab

#### `secrets-scan` - Secret Detection
- TruffleHog OSS for secret detection
- Full git history scanning
- Verified secrets only mode

#### `docker-security` - Docker Security Scan
- Trivy scanning of Docker images
- SARIF upload to Security tab
- Comprehensive container vulnerability analysis

#### `security-report` - Security Report Summary
- Aggregates all security scan results
- Generates markdown summary report
- 90-day artifact retention

### 4. Release (`release.yml`)

**Triggers:**
- Git tags starting with `v*`
- Manual dispatch with version input

**Jobs:**

#### `validate-release` - Validate Release
- Full test suite execution
- Package building and validation
- Quality gate before release

#### `create-release` - Create GitHub Release
- Automatic changelog generation
- GitHub release creation
- Asset upload URL provisioning

#### `build-assets` - Build Release Assets
- Python wheel and source distribution
- Upload to GitHub release

#### `publish-docker` - Publish Docker Images
- Release-tagged Docker images
- Multi-platform container publishing
- GitHub Container Registry

#### `publish-pypi` - Publish to PyPI
- Automated PyPI publishing
- Trusted publisher workflow
- Package distribution

## Automated Dependency Management

### Dependabot (`dependabot.yml`)

Automated dependency updates for:

- **Python dependencies** - Weekly on Mondays
- **Docker dependencies** - Weekly on Tuesdays
- **GitHub Actions** - Weekly on Wednesdays

Configuration includes:
- Automatic reviewers and assignees
- Semantic commit messages
- Appropriate labels
- Rebase strategy
- Sensible ignore rules for major updates

## Security Features

### CodeQL Configuration (`.github/codeql/codeql-config.yml`)

- Security and quality query suites
- Extended security analysis
- Focused on `stream_sniper/` source code
- Excludes test fixtures and virtual environments

### Security Scanning Coverage

1. **Dependency Vulnerabilities**
   - Known CVE database checks
   - Python package vulnerability scanning
   - Weekly automated scans

2. **Code Security**
   - Static analysis for security patterns
   - Common vulnerability detection
   - Secret scanning in git history

3. **Container Security**
   - Base image vulnerability scanning
   - Container configuration analysis
   - Multi-layer security assessment

## Workflow Integration

### Branch Protection
Recommended branch protection rules for `main`:
- Require status checks: `lint`, `test`, `docker-test`
- Require branches to be up to date
- Restrict pushes to users with push access

### Status Badges
The following badges are available in README.md:
- CI Pipeline status
- Docker Build status
- Security Scanning status
- Python version support
- License information

## Environment Variables and Secrets

### Required Secrets
- `GITHUB_TOKEN` - Automatically provided
- PyPI publishing requires trusted publisher setup

### Environment Variables
- `TEST_DB_*` - Test database configuration
- `TWITCH_USERNAME` - For integration testing

## Usage Examples

### Manual Workflow Dispatch
```bash
# Trigger security scan
gh workflow run security.yml

# Trigger release (manual)
gh workflow run release.yml -f version=v2.1.0
```

### Local Development
```bash
# Run the same checks locally
black --check .
isort --check-only .
flake8 stream_sniper/ tests/
mypy stream_sniper/
pytest tests/

# Build and test Docker images
docker-compose build
docker-compose up -d api
```

### Release Process
1. Update version in `pyproject.toml`
2. Create and push git tag: `git tag v2.1.0 && git push origin v2.1.0`
3. Release workflow automatically creates GitHub release and publishes packages

## Monitoring and Troubleshooting

### Workflow Logs
- All workflow runs are logged and available in the Actions tab
- Artifacts are retained for security reports (30-90 days)
- Failed runs trigger notifications

### Security Alerts
- Security vulnerabilities are reported in the Security tab
- Dependabot creates PRs for vulnerable dependencies
- CodeQL findings are integrated with GitHub's security features

### Performance Optimization
- Build caches are used for Docker and Python dependencies
- Matrix strategies run in parallel for efficiency
- Conditional job execution based on event type
