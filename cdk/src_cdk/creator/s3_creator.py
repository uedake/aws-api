from __future__ import annotations

from aws_cdk import Stack, RemovalPolicy
from aws_cdk.aws_s3 import Bucket, BlockPublicAccess


class S3Creator:
    def __init__(
        self,
        scope: Stack,
        bucket_name: str,
        *,
        public_read: bool | None = None,
        website_hosting: bool | None = None,
        website_index_document: str = "index.html",
    ) -> None:
        self.scope = scope

        if public_read is None:
            public_read = False
        if website_hosting is None:
            website_hosting = False

        self.bucket = Bucket(
            scope,
            bucket_name,
            bucket_name=bucket_name,
            public_read_access=public_read,
            block_public_access=(
                BlockPublicAccess.BLOCK_ACLS
                if public_read
                else BlockPublicAccess.BLOCK_ALL
            ),
            website_index_document=website_index_document if website_hosting else None,
            removal_policy=RemovalPolicy.DESTROY,
        )
