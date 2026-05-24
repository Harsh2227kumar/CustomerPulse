# Amazon RDS PostgreSQL - Account 1

Account 1 owns the PostgreSQL database. In the current project this service is
already working; use this guide to recreate it or verify its configuration.

## Purpose

PostgreSQL stores only the complaints selected from the frontend import page.
The full 8 GB CSV stays in Account 3 S3 and is not copied into RDS.

## Create The Database

1. Sign in to **AWS Account 1**.
2. Open **Amazon RDS**.
3. Select the AWS region where the shared database should remain.
4. Open **Databases** and click **Create database**.
5. Select **Standard create** so security and storage settings are visible.
6. Select engine type **PostgreSQL**.
7. Select a supported PostgreSQL engine version.
8. Under templates, choose **Free tier** for development when available, or a
   small development instance class appropriate to the account.
9. Enter the DB instance identifier:

   ```text
   customerpulse-postgres
   ```

10. Enter a master username, for example:

    ```text
    postgres
    ```

11. Create a strong password, or use AWS Secrets Manager where available.
12. Set the initial database name:

    ```text
    customerpulse
    ```

13. Keep storage encryption enabled.
14. Set backup retention appropriate to the environment.

## Development Networking

For a local laptop backend, the RDS instance must be reachable from your
computer.

1. In RDS creation or modification settings, set **Public access** only when
   needed for temporary development access.
2. Open the RDS security group in **EC2 > Security Groups**.
3. Add an inbound rule:

   | Type | Port | Source |
   | --- | --- | --- |
   | PostgreSQL | `5432` | Your current laptop public IP only |

4. Do not use `0.0.0.0/0` for PostgreSQL access.

For stable hosting later, do not depend on public database access. Connect
Account 3 EC2 to Account 1 RDS through controlled network connectivity and
restricted security rules.

## Find The Connection Values

1. Open **RDS > Databases > customerpulse-postgres**.
2. Open **Connectivity & security**.
3. Copy:
   - Endpoint
   - Port, normally `5432`
   - Database name
   - Username

## Backend Environment Value

Put the connection URL only in the local backend `.env` file or secret store:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@RDS_HOST:5432/customerpulse
DATABASE_ADMIN_URL=
```

Do not put this URL into a Git commit.

## Validate From The Backend

From the backend folder, the application setup command verifies schema and
database access:

```powershell
python -m app.db.setup
```

The application is expected to create or verify its complaint table and related
database requirements. If connection fails, first check the endpoint, password,
security group IP rule, and RDS availability state.

## Production Note

Create a restricted application database user instead of using the master user
for stable production hosting.

## Official AWS Reference

https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_GettingStarted.CreatingConnecting.PostgreSQL.html
