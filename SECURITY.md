# Security Policy

Ignition reviews other people's code, so we hold ourselves to a high bar on security. If you find a vulnerability, we want to know before anyone else does.

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email **suchitchopade3110@gmail.com** with:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept code or requests are welcome)
- Any relevant logs, screenshots, or affected endpoints/versions

We aim to:
- Acknowledge your report within **3 business days**
- Provide an initial assessment within **7 business days**
- Keep you updated as we investigate and remediate

## Scope

In scope:
- The Ignition backend API and webhook handlers (`app/`)
- The Ignition frontend/dashboard (`frontend/`)
- The GitHub App integration (installation, OAuth, webhook signature verification)
- Infrastructure misconfigurations affecting production (`render.yaml`, `docker-compose.yml`)

Out of scope:
- Vulnerabilities in third-party dependencies without a demonstrated exploit path against Ignition itself (report these upstream)
- Social engineering, physical security, or denial-of-service testing
- Automated scanner output with no verified impact

## Supported Versions

Ignition is deployed as a single hosted service (not versioned client software). The `main` branch running in production is always the supported version — there are no older versions to patch separately.

## Disclosure

We follow coordinated disclosure. Please give us a reasonable window to fix a confirmed issue before any public disclosure. We're happy to credit reporters (with permission) once a fix ships.

## Safe Harbor

We will not pursue legal action against researchers who:
- Make a good-faith effort to avoid privacy violations, data destruction, and service disruption
- Only interact with accounts/data they own or have explicit permission to test
- Report findings promptly through the channel above rather than exploiting them further
