# Three-Account CFPB S3 Setup

## Architecture

```text
Account 1: PostgreSQL RDS
Account 2: Bedrock Claude API key
Account 3: Private S3 bucket now, backend EC2 later
```

The FastAPI backend is always the bridge:

```text
Account 3 S3 CSV/ZIP -> FastAPI backend -> Account 1 RDS PostgreSQL
                           |
                           -> Account 2 Bedrock for later AI processing
```

PostgreSQL does not read S3 directly.

## Phase 1: Development On A Local Computer

### 1. Create The S3 Bucket In Account 3

In the AWS Console, sign in to Account 3, open S3, and create a general-purpose
bucket:

- Choose a globally unique bucket name, for example
  `customerpulse-cfpb-data-yourname`.
- Choose the application region, for example `ap-south-1`.
- Keep **Block all public access** enabled.
- Enable versioning.
- Leave default server-side encryption enabled.

Alternatively, with AWS CLI access to Account 3, deploy the provided template:

```powershell
$env:AWS_PROFILE="account3"
aws cloudformation deploy `
  --template-file infra/aws/s3/cfpb-data-bucket.yaml `
  --stack-name customerpulse-cfpb-data `
  --region ap-south-1 `
  --parameter-overrides BucketName=REPLACE_WITH_ACCOUNT3_BUCKET_NAME
```

### 2. Upload The CFPB CSV Or ZIP

In the bucket, upload the source file to this key:

```text
raw/cfpb/complaints.csv.zip
```

With AWS CLI:

```powershell
$env:AWS_PROFILE="account3"
aws s3 cp "D:\Download\complaints.csv.zip" `
  "s3://REPLACE_WITH_ACCOUNT3_BUCKET_NAME/raw/cfpb/complaints.csv.zip" `
  --region ap-south-1
```

### 3. Give Your Local Development Identity Read Access

In Account 3, attach the policy from:

```text
infra/aws/s3/backend-s3-read-policy.json.template
```

to the IAM user or role used by your local AWS profile. Replace
`REPLACE_WITH_ACCOUNT3_BUCKET_NAME` first.

Configure a named local profile:

```powershell
aws configure --profile customerpulse-s3-dev
$env:AWS_PROFILE="customerpulse-s3-dev"
aws sts get-caller-identity
aws s3api head-object `
  --bucket REPLACE_WITH_ACCOUNT3_BUCKET_NAME `
  --key raw/cfpb/complaints.csv.zip `
  --region ap-south-1
```

### 4. Configure The Local Backend

Keep RDS and Bedrock values from their existing accounts, and add Account 3 S3:

```env
# Account 1
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@RDS_HOST:5432/customerpulse

# Account 2
AI_PROVIDER=bedrock
BEDROCK_API_KEY=replace_with_account2_bedrock_key
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6

# Account 3
S3_BUCKET_NAME=REPLACE_WITH_ACCOUNT3_BUCKET_NAME
CFPB_S3_KEY=raw/cfpb/complaints.csv.zip
AWS_REGION=ap-south-1
```

Start the backend from a terminal where `AWS_PROFILE=customerpulse-s3-dev` is set.
The frontend Import page can then preview selected CSV rows and insert only those
rows into Account 1 PostgreSQL.

## Phase 2: Stable Hosting On EC2 In Account 3

Create an EC2 IAM role in Account 3, for example `CustomerPulseBackendRole`, with:

- Trust relationship for the EC2 service.
- The same `backend-s3-read-policy.json.template` permission attached after
  replacing the bucket name.

Attach that role to the Account 3 EC2 instance. Because S3 and EC2 are both in
Account 3, do not place long-term AWS access keys in the EC2 `.env`; boto3 will
use the instance role automatically.

The EC2 deployment `.env` keeps the same three-account values:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@ACCOUNT1_RDS_HOST:5432/customerpulse
BEDROCK_API_KEY=replace_with_account2_bedrock_key
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6
S3_BUCKET_NAME=REPLACE_WITH_ACCOUNT3_BUCKET_NAME
CFPB_S3_KEY=raw/cfpb/complaints.csv.zip
AWS_REGION=ap-south-1
```

EC2 in Account 3 must separately be allowed to reach RDS in Account 1 on
PostgreSQL port `5432`. For stable hosting, use private cross-account VPC
connectivity where possible; during a temporary demo, use narrowly restricted
RDS network access only if necessary.

## Encryption Default

The template uses S3-managed encryption (`AES256`). If you later change the
bucket to a customer-managed KMS key, also grant the local/EC2 role permission
to decrypt with that KMS key.
