# Amazon Bedrock Claude - Account 2

Account 2 owns Bedrock Claude access. In the current project Bedrock is already
working; use this guide when recreating development access or renewing an
expired development API key.

## Purpose

Bedrock performs AI analysis after selected complaints have been imported into
PostgreSQL. S3 filtering and Athena querying are independent of Bedrock.

## Enable Anthropic Claude Access

1. Sign in to **AWS Account 2**.
2. Open **Amazon Bedrock**.
3. Select the region used by the backend configuration. The current project
   uses:

   ```text
   us-east-1
   ```

4. In **Model catalog** or **Model access**, locate the Anthropic Claude model
   required by the application.
5. Complete any requested Anthropic use-case details.
6. Confirm the model is available for invocation in that region.

Model availability and access screens can change over time; always select a
model ID that is available in the chosen region.

## Create A Development API Key

The current backend uses a Bedrock API key during development.

1. In Bedrock, open **API keys**.
2. Open the **Long-term API keys** tab.
3. Click **Generate long-term API keys**.
4. Choose an expiration period suitable for development.
5. Generate the key.
6. Copy it immediately and keep it private; AWS displays it only once.

AWS recommends long-term Bedrock API keys for development and exploration, not
for stable production applications.

## Backend Environment Values

Put these settings in the backend `.env`, not in Git:

```env
AI_PROVIDER=bedrock
BEDROCK_API_KEY=replace_with_account2_bedrock_key
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6
BEDROCK_BASE_URL=
```

Use the `BEDROCK_MODEL` value already verified by the project unless you
intentionally update backend model support.

## Verify

1. Start the backend with `.env` configured.
2. Import a small complaint selection into PostgreSQL.
3. Use the application Process action on one imported complaint.
4. Confirm the result is stored and appears in the frontend.

For backend readiness on a new machine, run the setup script before starting
the app so Python requirements, database schema, Bedrock connectivity, and the
MiniLM embedding model cache are checked together:

```bash
VERIFY_EMBEDDING=true bash backend/scripts/setup_backend.sh
```

On Windows:

```powershell
backend\scripts\setup_backend.ps1 -VerifyEmbedding
```

## Key Rotation

When a development API key expires:

1. Generate a replacement key in Account 2 Bedrock.
2. Update the local `.env` value.
3. Restart the backend.
4. Delete or disable the old credential where applicable.

## Future Hosting Note

For stable hosting, review AWS's temporary credential or role-based alternatives
instead of copying a long-term Bedrock key to an EC2 machine.

## Official AWS References

- https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started-api-keys.html
