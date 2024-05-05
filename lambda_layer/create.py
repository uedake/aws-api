import argparse

from command import create_layer

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="output layer.zip at current working directory"
    )

    parser.add_argument("pip_install_args", nargs="*")
    parser.add_argument(
        "-p", "--python_version", help="python_version e.g. 3.12.3", default="3.12.3"
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

    zip_name = f"al{args.amazon_linux_version}py{args.python_version}.zip"
    create_layer(
        " ".join(args.pip_install_args),
        zip_name,
        python_version=args.python_version,
        amazon_linux_version=args.amazon_linux_version,
        image_tag=image_tag,
    )
