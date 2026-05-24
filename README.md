# CustomerPulse Backend

FastAPI backend for CustomerPulse complaint ingestion and AWS Bedrock Claude enrichment. This feature branch contains backend source and backend runtime support files only.

Backend setup is automatic on startup, and can also be run manually:

```bash
cd backend
python -m app.db.setup
```

Fill `.env` from `.env.template` before running the backend. Set the PostgreSQL, Bedrock, and private S3 configuration values through local or deployment-managed environment settings. Never commit real secrets.

For the production-size CFPB source, use `CFPB_INGESTION_MODE=athena`. The raw
CFPB CSV includes multiline complaint narratives, which Athena's CSV reader
cannot safely parse. Run `backend/glue/cfpb_csv_to_parquet.py.template` once as
an AWS Glue job in Account 3, then run
`backend/sql/athena_cfpb_parquet_registration.sql.template` in Athena to
register the generated Parquet data. The import page then loads filter values
and bounded selections from Athena rather than scanning the 8 GB CSV on each
request. `CFPB_INGESTION_MODE=csv` remains available only for small local test
files.

The API exposes complaint querying through `GET /api/complaints`, S3 import through `/api/ingestion/s3/*`, and Bedrock processing through `POST /api/process` or `POST /api/process/{complaint_id}` for imported rows.

Run the backend container independently:

```bash
docker compose up --build
```
