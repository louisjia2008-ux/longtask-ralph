# Project Profiles

Use these profiles to choose verification and task granularity. A repository may match multiple profiles.

## Generic Repository

- **Identify**: no dominant build file, mixed scripts/docs/assets.
- **Verifier**: static checks for JSON, shell syntax, Python syntax/compileall, file existence checks.
- **Risks**: broad edits without a build signal.
- **Do not auto-do**: mass formatting, dependency changes, cleanup outside task scope.
- **Atomic task size**: one file group, one script, one documented behavior.

## Documentation Project

- **Identify**: many `.md`, `.mdx`, docs folders, no app build.
- **Verifier**: link checks if available, markdown lint if configured, static sanity.
- **Risks**: changing meaning, removing examples, breaking docs navigation.
- **Do not auto-do**: rewrite large sections without acceptance criteria.
- **Atomic task size**: one page, one section, or one broken-link group.

## Node / JS / TS

- **Identify**: `package.json`.
- **Verifier**: available npm scripts: `test`, `lint`, `typecheck`, `build`.
- **Risks**: dependency churn, lockfile changes, generated artifacts.
- **Do not auto-do**: install or upgrade dependencies unless the task requires it.
- **Atomic task size**: one failing test group, one component, one lint/type error group.

## Python

- **Identify**: `pyproject.toml`, `requirements.txt`, `setup.py`.
- **Verifier**: `python3 -m compileall .`, `pytest` if available.
- **Risks**: virtualenv noise, import side effects, broad formatting.
- **Do not auto-do**: modify env files or install packages without need.
- **Atomic task size**: one module, one failing test, one import/type issue group.

## Rust

- **Identify**: `Cargo.toml`.
- **Verifier**: `cargo check`, `cargo test` when tests exist or when safe.
- **Risks**: long builds, lockfile changes, feature flags.
- **Do not auto-do**: publish crates or broad dependency upgrades.
- **Atomic task size**: one compiler error group, one module, one test failure.

## Go

- **Identify**: `go.mod`.
- **Verifier**: `go test ./...`.
- **Risks**: module downloads, generated files, platform-specific tests.
- **Do not auto-do**: change module path or run deploy scripts.
- **Atomic task size**: one package or one failing test group.

## Java / Maven

- **Identify**: `pom.xml`.
- **Verifier**: `mvn test`.
- **Risks**: long test suites, integration tests needing services.
- **Do not auto-do**: deploy artifacts, change repositories, publish packages.
- **Atomic task size**: one module, one test class, one compiler error group.

## Godot

- **Identify**: `project.godot`.
- **Verifier**: `godot --headless --path . --quit` if available; otherwise static checks and soft warning.
- **Risks**: scene file churn, indentation damage, warning-as-error, missing `res://` paths.
- **Do not auto-do**: mass rewrite scenes or reorder resources.
- **Atomic task size**: one warning group, one script path issue, one scene/script mismatch.

## Static Website

- **Identify**: `index.html`, site generator config, assets/css/js with no full app framework.
- **Verifier**: configured build, basic HTML/CSS/JS sanity, link checks if available.
- **Risks**: visual regressions, asset path breakage, responsiveness.
- **Do not auto-do**: redesign unrelated pages.
- **Atomic task size**: one page, one responsive bug, one asset path group.

## Data / Report Project

- **Identify**: spreadsheets, notebooks, CSV/JSON data, report scripts.
- **Verifier**: script dry-runs, schema checks, JSON/CSV parsing, generated report existence.
- **Risks**: overwriting source data, leaking private data, nondeterministic generated output.
- **Do not auto-do**: delete raw data, call paid APIs, publish reports.
- **Atomic task size**: one dataset validation, one chart/report section, one script fix.
