import io
import json
import zipfile

import moto
import boto3

from rvm import rvm

PIPELINE_BUCKET = "RvmPipelineBucket"
CONFIG_FILE = "rvm-configuration.zip"


@moto.mock_aws
def test_create_stack(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    s3 = boto3.resource("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=PIPELINE_BUCKET)
    pipeline_bucket = s3.Bucket(PIPELINE_BUCKET)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        manifest_data = json.dumps(
            {
                "templates": [
                    {
                        "template_file": "templates/stack1.template",
                        "accounts": ["111111111111", "222222222222"],
                    },
                    {
                        "template_file": "templates/stack2.template",
                        "accounts": ["222222222222"],
                    },
                ]
            },
        )
        zipf.writestr("manifest.json", manifest_data)

        template1_yaml = "Resources:\n  MyBucket:\n    Type: AWS::S3::Bucket\n"
        zipf.writestr("templates/stack1.template", template1_yaml)

        template2_yaml = "Resources:\n  MyOtherBucket:\n    Type: AWS::S3::Bucket\n"
        zipf.writestr("templates/stack2.template", template2_yaml)

    zip_buffer.seek(0)
    pipeline_bucket.upload_fileobj(zip_buffer, CONFIG_FILE)

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": PIPELINE_BUCKET},
                    "object": {"key": CONFIG_FILE},
                }
            },
        ]
    }

    response = rvm.lambda_handler(event, None)
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["success"] == [
        "templates/stack1.template:111111111111",
        "templates/stack1.template:222222222222",
        "templates/stack2.template:222222222222",
    ]
    assert body["failed"] == []
