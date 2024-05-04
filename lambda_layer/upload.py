import argparse

from util.aws_upload_util import LambdaLayerUploader

from mypy_boto3_ecr import ECRClient  # from boto3-stubs


def upload_layer(
    zip_path: str,
    layer_name: str,
    runtime: str,
):
    LambdaLayerUploader(layer_name, runtime).upload(zip_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", help="path to lambda layer zip file")
    parser.add_argument("layer", help="name of layer")
    parser.add_argument(
        "runtime", help="runtime type e.g. python3.12", default="python3.12"
    )
    args = parser.parse_args()
    upload_layer(args.zip_path, args.layer, args.runtime)
