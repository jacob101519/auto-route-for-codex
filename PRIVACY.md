# Privacy

Auto Route for Codex is designed to route from bounded task characteristics, not raw task content.

The public router does not implement telemetry, network calls, session-file access, persistent recommendation state, task transfer, or credential storage. It rejects unknown input fields.

Repository verification scans exported files for local paths, UUID-shaped task identifiers, configured private fingerprints, and common secret-value patterns. These checks reduce accidental disclosure but cannot prove that prose is non-sensitive; release review remains required.

When reporting an Issue, remove prompts, proprietary code, personal data, and host identifiers unless they are essential and safe to share. Use private vulnerability reporting for security-sensitive material.

See [docs/privacy-and-data-flow.md](docs/privacy-and-data-flow.md) for the technical data-flow boundary.
