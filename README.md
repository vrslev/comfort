# ERP for IKEA delivery company

## What is this

This is a job placement demo for reference that probably won't be particularly useful to you.

If you find here anything useful, you can use it.

## Software stack

- [Frappe Framework](https://github.com/frappe/frappe): Python, JavaScript
- Docker, Docker Compose, [Docker Buildx Bake](https://docs.docker.com/build/bake/)
- Yandex.Cloud: VM, S3, Serverless

## "What's this" by directory

### `.github/`

Tests, docker build, deployment, backup, dependency updates.

### `browser_ext/`

Chrome extension and Apple Automator script (for Safari) for crawling IKEA's authorization token from cookies. Script also allows to quickly add orders from VK.

### `cli/`

Convenience tool to speed up development day.

### `comfort/`

Everything essential. More stuff than I can explain in 5 minutes.

### `tests/`

A bunch of tests for `comfort/`.

