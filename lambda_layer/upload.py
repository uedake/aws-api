import argparse

from command import upload_layer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="upload zip file to AWS lambda layer")
    parser.add_argument("zip_path", help="path to lambda layer zip file")
    parser.add_argument("layer", help="name of layer")
    parser.add_argument(
        "-s",
        "--skip",
        action="store_true",
        help="skip uploading if description is same with the latest version in AWS",
    )
    parser.add_argument("-d", "--description", help="description of layer")
    parser.add_argument(
        "-r", "--runtime", help="runtime type e.g. python3.12", default="python3.13"
    )
    args = parser.parse_args()
    upload_layer(
        args.zip_path,
        args.layer,
        args.runtime,
        description=args.description,
        skip_same_description=args.skip,
    )
