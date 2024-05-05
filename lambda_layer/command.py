import os

from util.docker_util import Docker
from util.aws_upload_util import LambdaLayerUploader


def create_and_upload_layer(
    layer_name: str,
    pip_install_args: str,
    zip_name: str,
    *,
    amazon_linux_version: str,
    python_version: str,
    runtime: str,
    image_tag: str,
):

    success, installed = create_layer(
        pip_install_args,
        zip_name,
        amazon_linux_version=amazon_linux_version,
        python_version=python_version,
        image_tag=image_tag,
    )

    if success:
        mount_path = os.path.join(os.path.dirname(__file__), "mount")
        upload_layer(
            os.path.join(mount_path, zip_name),
            layer_name,
            runtime,
            description=f"{python_version}:{installed}",
            skip_same_description=True,
        )


def upload_layer(
    zip_path: str,
    layer_name: str,
    runtime: str,
    *,
    description: str | None = None,
    skip_same_description: bool = False,
):
    LambdaLayerUploader(layer_name, runtime).upload(
        zip_path, description=description, skip_same_description=skip_same_description
    )


def create_layer(
    pip_install_args: str,
    zip_name: str,
    *,
    amazon_linux_version: str,
    python_version: str,
    image_tag: str,
) -> tuple[bool, str]:
    docker_path = os.path.join(
        os.path.dirname(__file__), "docker", f"amazonlinux{amazon_linux_version}"
    )
    docker = Docker(image_tag)
    print("[BUILD IMAGE] please wait a few minutes")
    docker.build(
        docker_path,
        build_args={
            "PYTHON_VER": python_version,
        },
    )
    print("[RUN CONTAINER]")
    mount_path = os.path.join(os.path.dirname(__file__), "mount")

    success, installed = docker.run(mount_path, f"{zip_name} {pip_install_args}")
    if success:
        print(f"layerを作成しました：{installed}")
    else:
        print("layerの作成に失敗しました")
    return success, installed
