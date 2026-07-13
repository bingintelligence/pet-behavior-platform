# Contributing Guide

Thank you for your interest in contributing to the Pet Behavior Platform!

We welcome bug reports, feature requests, documentation improvements, and code contributions. This guide describes our development workflow and coding standards.

---

# Development Workflow

1. Fork the repository.
2. Create a feature branch from `main`.

```bash
git checkout -b feature/<feature-name>
```

Example:

```text
feature/image-upload
feature/video-analysis
fix/upload-timeout
```

3. Make your changes.

4. Run formatting, linting, and tests before submitting.

```bash
make lint
make test
```

5. Commit your changes using meaningful commit messages.

Examples:

```text
feat: add image preprocessing pipeline

fix: resolve inference timeout issue

docs: update deployment guide

refactor: simplify queue consumer
```

6. Push your branch.

7. Open a Pull Request.

---

# Pull Request Requirements

Each Pull Request should:

* Include a clear description.
* Explain the motivation for the change.
* Reference related issues when applicable.
* Pass all CI checks.
* Include tests for new functionality.
* Update documentation if behavior changes.

---

# Coding Standards

## Python

* Follow PEP 8.
* Use type hints whenever possible.
* Write descriptive function and variable names.
* Keep functions focused on a single responsibility.

Example:

```python
def analyze_behavior(video_path: str) -> BehaviorResult:
    ...
```

---

## API Design

* Use RESTful APIs.
* Return consistent JSON responses.
* Use proper HTTP status codes.
* Version APIs under `/v1`.

Example:

```text
POST /v1/analysis/jobs

GET /v1/analysis/jobs/{job_id}
```

---

## Kubernetes

Every service should provide:

* Dockerfile
* Helm chart
* Health endpoint
* Readiness probe
* Liveness probe
* Prometheus metrics

---

## Testing

Every feature should include:

* Unit tests
* Integration tests (if applicable)

End-to-end tests are required for major user-facing functionality.

---

# Branch Naming

Feature:

```text
feature/<feature-name>
```

Bug Fix:

```text
fix/<bug-name>
```

Documentation:

```text
docs/<topic>
```

Infrastructure:

```text
infra/<change>
```

---

# Issue Reporting

Please include:

* Environment
* Reproduction steps
* Expected behavior
* Actual behavior
* Logs (if available)
* Screenshots (if applicable)

---

# Security

Do not submit:

* Secrets
* API keys
* Passwords
* Tokens
* Private datasets
* Model weights

Report security vulnerabilities privately instead of opening a public issue.

---

# Code Review

Every Pull Request requires:

* CI passing
* At least one reviewer approval
* No unresolved comments

Large architectural changes should include a design proposal before implementation.

---

# Documentation

Update documentation when changing:

* APIs
* Architecture
* Deployment
* Configuration
* User-facing functionality

Documentation lives under:

```text
docs/
```

---

# Community Guidelines

Be respectful.

Provide constructive feedback.

Assume positive intent.

Help make the project welcoming to contributors of all experience levels.
