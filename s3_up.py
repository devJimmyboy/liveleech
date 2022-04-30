import os
import boto3

# Step 2: The new session validates your request and directs it to your Space's specified endpoint using the AWS SDK.
# client: boto3.client.
session = boto3.Session()
client = session.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT"),
    region_name=os.getenv("S3_REGION"),
    aws_access_key_id=os.getenv("S3_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET"),
)


def start_multi(bucket, key):
    return client.create_multipart_upload(
        ACL="public-read",
        Bucket=bucket,
        Key=key,
        ContentType="video/x-flv",
    )


def upload_part(bucket, key, part_num, part_data, upload_id):
    client.upload_part(
        Bucket=bucket, Key=key, PartNumber=part_num, UploadId=upload_id, Body=part_data
    )


def upload_file(bucket, key, file_path, channel_name):
    client.put_object(
        Bucket=os.path.join(
            os.getenv("S3_BUCKET"), channel_name
        ),  # The path to the directory you want to upload the object to, starting with your Space name.
        Key="hello-world.txt",  # Object key, referenced whenever you want to access this file later.
        Body=b"Hello, World!",  # The object's contents.
        ACL="private",  # Defines Access-control List (ACL) permissions, such as private or public.
        Metadata={"x-amz-meta-my-key": "your-value"},  # Defines metadata tags.
    )
