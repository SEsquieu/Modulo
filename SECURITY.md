# Security

## Project status

Modulo is experimental alpha software for trusted local and private-network environments.

The current control plane and worker protocol do **not** provide:

- authentication or authorization
- TLS termination
- tenant isolation
- durable audit storage
- request encryption beyond any protection supplied by an external network/tunnel
- sandboxing or attestation for worker machines
- protection against a malicious worker, client, or control plane

Do not bind the server to an Internet-facing interface without an authenticated, encrypted access layer in front of it. Do not send secrets or sensitive prompts through workers you do not control.

A private network identifier is a routing constraint, not a security credential.

## Supported versions

Security fixes currently target the latest commit on `main`. There is no stable compatibility or long-term-support promise during alpha development.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose user data, credentials, or machines.

Report it privately through GitHub's **Security** tab using a private vulnerability report. If private reporting is unavailable, contact the maintainer through the email address on the maintainer's GitHub profile and include `Modulo security` in the subject.

Include the affected revision, reproduction steps, impact, and any suggested mitigation. Please avoid accessing data or systems that are not yours while validating a report.

## Credential hygiene

Modulo should never commit runtime credentials, tunnel tokens, private keys, or populated environment files. If a credential has entered Git history, rotate it before rewriting history; removing the visible file is not sufficient.

