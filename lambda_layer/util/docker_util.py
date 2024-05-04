try:
    from docker.client import DockerClient
    from docker.errors import BuildError

    DOCKER_NOT_FOUND = False
except Exception:
    print("docker python package not found")
    DOCKER_NOT_FOUND = True

class DockerClient:
    def __init__(self,username:str|None=None,password:str|None=None,registry:str|None=None):
        assert(not DOCKER_NOT_FOUND)
        self.docker_client = DockerClient.from_env()

        if username is not None and password is not None and registry is not None:
            self.docker_client.login(
                username, password, registry
            )

    def build(self,docker_file_folder_path:str,tag:str,build_args):
        self.docker_client.images.build(
            path=docker_file_folder_path, tag=tag, buildargs=build_args, rm=True
        )

    def run(self):
        pass