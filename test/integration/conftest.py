import os
import subprocess

import tempfile
import uuid

import pytest


@pytest.fixture
def build_dir_and_ee_yml():
    """Fixture to return temporary file maker."""

    def tmp_dir_and_file(ee_contents):
        tmpdir = tempfile.mkdtemp(prefix="ansible-builder-test-")
        with tempfile.NamedTemporaryFile(delete=False, dir=tmpdir) as tempf:
            tempf.write(bytes(ee_contents, "UTF-8"))
        return tmpdir, tempf.name

    return tmp_dir_and_file


@pytest.fixture()
def ee_tag(request, cli, container_runtime):
    image_name = 'builder-test-' + str(uuid.uuid4())[:10]

    def delete_image():
        cli(f'{container_runtime} rmi -f {image_name}')

    request.addfinalizer(delete_image)
    return image_name


class CompletedProcessProxy(object):
    def __init__(self, result):
        self.result = result

    def __getattr__(self, attr):
        return getattr(self.result, attr)


@pytest.fixture(scope="function")
def cli(request):
    def run(args, *a, **kw):
        kw["encoding"] = "utf-8"
        if "check" not in kw:
            # By default we want to fail if a command fails to run. Tests that
            # want to skip this can pass check=False when calling this fixture
            kw["check"] = True
        if "stdout" not in kw:
            kw["stdout"] = subprocess.PIPE
        if "stderr" not in kw:
            kw["stderr"] = subprocess.PIPE

        kw.setdefault("env", os.environ.copy()).update({"LANG": "en_US.UTF-8"})

        try:
            ret = CompletedProcessProxy(subprocess.run(args, shell=True, *a, **kw))
        except subprocess.CalledProcessError as err:
            pytest.fail(
                f"Running {err.cmd} resulted in a non-zero return code: {err.returncode} - stdout: {err.stdout}, stderr: {err.stderr}"
            )

        return ret

    return run


@pytest.fixture(params=['docker', 'podman'], ids=['docker', 'podman'])
def container_runtime(request, cli):
    if cli(f'{request.param} --version', check=False).returncode == 0:
        return request.param
    else:
        pytest.skip(f'{request.param} runtime not available')
