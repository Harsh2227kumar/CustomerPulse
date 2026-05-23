# Cross-Account CFPB S3 Setup

## Data Flow

```text
Account 2 private S3 CSV/ZIP
        -> Account 1 backend role reads selected rows
        -> Account 1 RDS PostgreSQL stores imported complaints
```

PostgreSQL does not fetch the CSV directly. The FastAPI backend reads S3 using its
AWS identity and inserts only rows selected from the import page.

## Values To Collect

- `ACCOUNT1_BACKEND_ROLE_ARN`: the IAM role used by the running backend, for
  example an Account 1 EC2 instance role.
- `ACCOUNT2_BUCKET_NAME`: a new globally unique private bucket name.
- `AWS_REGION`: the S3 region, for example `ap-south-1`.

## 1. Create The Bucket In Account 2

Sign in or configure an AWS CLI profile for Account 2, then deploy:

```powershell
$env:AWS_PROFILE="account2"
aws cloudformation deploy `
  --template-file infra/aws/s3/cfpb-data-bucket.yaml `
  --stack-name customerpulse-cfpb-data `
  --region ap-south-1 `
  --parameter-overrides `
    BucketName=REPLACE_WITH_ACCOUNT2_BUCKET_NAME `
    Account1BackendRoleArn=arn:aws:iam::ACCOUNT1_ID:role/CustomerPulseBackendRole
```

The template creates a private, versioned, S3-encrypted bucket and grants only the
specified Account 1 backend role access to objects under `raw/cfpb/`.

## 2. Allow The Backend Role In Account 1

In Account 1, create an inline IAM policy on the backend runtime role using:

```text
infra/aws/s3/account1-backend-s3-read-policy.json.template
```

Replace `REPLACE_WITH_ACCOUNT2_BUCKET_NAME` with the created bucket name. The
bucket policy in Account 2 and the role policy in Account 1 are both required.

## 3. Upload The CSV ZIP To Account 2

```powershell
$env:AWS_PROFILE="account2"
aws s3 cp "D:\Download\complaints.csv.zip" `
  "s3://REPLACE_WITH_ACCOUNT2_BUCKET_NAME/raw/cfpb/complaints.csv.zip" `
  --region ap-south-1
```

Supported backend source formats are `.csv` and `.zip` containing a CSV file.

## 4. Configure The Backend Runtime

Use these deployment-only values; do not commit the real bucket identifier or
credentials if they are sensitive in your project:

```env
S3_BUCKET_NAME=REPLACE_WITH_ACCOUNT2_BUCKET_NAME
CFPB_S3_KEY=raw/cfpb/complaints.csv.zip
AWS_REGION=ap-south-1
```

When the backend runs on EC2 in Account 1, attach
`CustomerPulseBackendRole` to that EC2 instance. Do not store AWS access keys in
the repository.

## 5. Verify Cross-Account Reading

Run from the backend host or using the Account 1 backend role:

```powershell
$env:AWS_PROFILE="account1-backend"
aws sts get-caller-identity
aws s3api head-object `
  --bucket REPLACE_WITH_ACCOUNT2_BUCKET_NAME `
  --key raw/cfpb/complaints.csv.zip `
  --region ap-south-1
```

After access succeeds, open the frontend S3 Import page, choose a Product such as
`Credit card`, set the maximum records, preview the selection, and import it.

## Encryption Default

The CloudFormation template uses S3-managed encryption (`AES256`). If you later
change the bucket to a customer-managed KMS key, the Account 1 backend role also
needs `kms:Decrypt`, and the KMS key policy in Account 2 must allow that role.
