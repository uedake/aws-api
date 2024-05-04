import argparse
import os

from util.docker_util import DockerClient

DOCKER_TAG="al2023py"

def create_layer(
    pip_install_args: str,
    python_version: str,
):
    docker_path=os.path.join(os.path.dirname(__file__), "docker")
    docker_client=DockerClient()
    docker_client.build(docker_path,DOCKER_TAG)
    docker_client.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("tag", nargs="*")
    parser.add_argument("pip_install_args", nargs="*")
    parser.add_argument("-v", help="python_version e.g. 3.12.3", default="3.12.3")
    args = parser.parse_args()
    create_layer(args.pip_install_args, args.python_version)
