# IAM Users, Groups, And Local Credentials - Account 3

Create separate identities for uploading files and reading/querying data.
Never use the friend's uploader credential in the backend.

## Final IAM Structure

| Type | Name | Used By | Purpose |
| --- | --- | --- | --- |
| Policy | `CustomerPulseUploadCfpbFiles` | Uploader group | Upload only |
| Group | `CustomerPulseS3Uploaders` | Friend uploader users | Manage upload permissions |
| User | one named user per uploader | Friend | Console CSV upload |
| Policy | `CustomerPulseReadCfpbFiles` | Reader group | Read raw CSV |
| Policy | `CustomerPulseAthenaRuntime` | Reader group | Query Parquet through Athena |
| Group | `CustomerPulseS3Readers` | Backend dev user | Manage backend permissions |
| User | `CustomerPulseBackendReaders` | Local backend | Access key for development |

## Create Uploader Group And Policy

1. In **Account 3**, open **IAM > User groups**.
2. Create group:

   ```text
   CustomerPulseS3Uploaders
   ```

3. Create an inline or customer-managed JSON policy named:

   ```text
   CustomerPulseUploadCfpbFiles
   ```

4. Use this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ShowBucketsInS3Console",
      "Effect": "Allow",
      "Action": "s3:ListAllMyBuckets",
      "Resource": "*"
    },
    {
      "Sid": "InspectUploadBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data"
    },
    {
      "Sid": "NavigateCfpbUploadFolder",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "",
            "raw",
            "raw/",
            "raw/cfpb",
            "raw/cfpb/",
            "raw/cfpb/*"
          ]
        }
      }
    },
    {
      "Sid": "UploadOnlyCfpbFiles",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data/raw/cfpb/*"
    }
  ]
}
```

The `s3:ListAllMyBuckets` action is needed for an IAM console user to browse
the S3 console bucket list. It shows bucket names in Account 3; it does not
permit reading bucket objects.

## Create A Friend Upload User

1. Go to **IAM > Users > Create user**.
2. Use a name identifying the friend, for example:

   ```text
   customerpulse-cfpb-uploader-friendname
   ```

3. Enable AWS Management Console access only if the friend will upload using
   the website.
4. Add the user to `CustomerPulseS3Uploaders`.
5. Give the login URL and temporary password privately.
6. Ask the user to upload only:

   ```text
   s3://customerpulse-cfpb-data/raw/cfpb/complaints.csv
   ```

## Create Backend Readers Group And Raw Read Policy

1. Go to **IAM > User groups > Create group**.
2. Name it:

   ```text
   CustomerPulseS3Readers
   ```

3. Create or attach the policy:

   ```text
   CustomerPulseReadCfpbFiles
   ```

4. Use this JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InspectCfpbBucketLocation",
      "Effect": "Allow",
      "Action": "s3:GetBucketLocation",
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data"
    },
    {
      "Sid": "ListCfpbImportFolder",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "raw/cfpb",
            "raw/cfpb/*"
          ]
        }
      }
    },
    {
      "Sid": "ReadCfpbImportFile",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data/raw/cfpb/*"
    }
  ]
}
```

## Add Athena Backend Runtime Policy

After Glue and Athena are used, the backend needs query permissions. Create a
second policy on `CustomerPulseS3Readers` named:

```text
CustomerPulseAthenaRuntime
```

Replace `REPLACE_WITH_ACCOUNT3_ID` before saving.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RunAthenaQueries",
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution",
        "athena:GetWorkGroup"
      ],
      "Resource": "arn:aws:athena:ap-south-1:REPLACE_WITH_ACCOUNT3_ID:workgroup/primary"
    },
    {
      "Sid": "ReadAthenaCatalogMetadata",
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetPartition",
        "glue:GetPartitions"
      ],
      "Resource": [
        "arn:aws:glue:ap-south-1:REPLACE_WITH_ACCOUNT3_ID:catalog",
        "arn:aws:glue:ap-south-1:REPLACE_WITH_ACCOUNT3_ID:database/customerpulse_data",
        "arn:aws:glue:ap-south-1:REPLACE_WITH_ACCOUNT3_ID:table/customerpulse_data/cfpb_parquet"
      ]
    },
    {
      "Sid": "InspectAthenaDataAndOutputBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data"
    },
    {
      "Sid": "ReadProcessedParquet",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data/processed/cfpb_parquet_glue/*"
    },
    {
      "Sid": "ReadWriteAthenaResults",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": "arn:aws:s3:::customerpulse-cfpb-data/athena/results/*"
    }
  ]
}
```

Athena must check the S3 result bucket before starting a query. Keep
`s3:GetBucketLocation` outside any `s3:prefix` condition. The runtime policy
above permits bucket inspection only for the one private CustomerPulse bucket,
reads only the processed Parquet data, and writes only Athena result objects.

## Create Backend Development User

1. Go to **IAM > Users > Create user**.
2. User name:

   ```text
   CustomerPulseBackendReaders
   ```

3. Do not enable AWS Console access.
4. Add the user to:

   ```text
   CustomerPulseS3Readers
   ```

5. Open the user's **Security credentials** tab.
6. Click **Create access key**.
7. For use case, select **Local code**.
8. Download the key CSV once and store it securely.

## Configure The Laptop Without AWS CLI

The AWS Console creates the key; the locally running backend still needs the
key on the laptop.

1. In File Explorer, create:

   ```text
   C:\Users\ACER\.aws
   ```

2. In Notepad, create a file with no `.txt` extension:

   ```text
   C:\Users\ACER\.aws\credentials
   ```

3. Add the key values from the downloaded credential CSV:

```ini
[default]
aws_access_key_id = REPLACE_WITH_ACCESS_KEY_ID
aws_secret_access_key = REPLACE_WITH_SECRET_ACCESS_KEY
```

4. Create:

   ```text
   C:\Users\ACER\.aws\config
   ```

5. Add:

```ini
[default]
region = ap-south-1
output = json
```

Do not send key values to anyone and do not commit either local credential
file.

## Later On EC2

Do not place these access keys on EC2. Create and attach an EC2 IAM role using
the Athena/S3 runtime permissions described in
`08_PHASE2_EC2_ACCOUNT3.md`.

## Official AWS References

- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_groups_create.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html
