# CustomerPulse Infrastructure

Infrastructure and deployment configuration for CustomerPulse. This feature branch contains infrastructure assets and root orchestration files only; application source is published from its own feature branches.

The Compose definition runs an externally built backend image behind Nginx. Prepare deployment-only settings first:

```bash
cp .env.template .env
# Fill the deployment values in .env.
docker compose up -d
```

Fill deployment values from `.env.template` locally or through managed deployment settings. Never commit real secrets.
