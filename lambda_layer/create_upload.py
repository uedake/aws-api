import argparse

from command import create_and_upload_layer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="create lambda layer and upload it")

    parser.add_argument("layer", help="name of layer")
    parser.add_argument("pip_install_args", nargs="*")
    parser.add_argument(
        "-p", "--python_version", help="python_version e.g. 3.12.3", default="3.13"
    )
    parser.add_argument(
        "-a",
        "--amazon_linux_version",
        help="amazon_linux_version e.g. 2023",
        default="2023",
    )
    args = parser.parse_args()
    pv: str = args.python_version
    image_tag = f"lambda-layer-build:al{args.amazon_linux_version}py{pv}"
    runtime = "python{}".format(".".join(pv.split(".")[0:2]))

    zip_name = f"al{args.amazon_linux_version}py{args.python_version}.zip"
    create_and_upload_layer(
        args.layer,
        " ".join(args.pip_install_args),
        zip_name,
        python_version=args.python_version,
        amazon_linux_version=args.amazon_linux_version,
        image_tag=image_tag,
        runtime=runtime,
    )
