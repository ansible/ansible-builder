import os
import subprocess

import tempfile
import uuid

import pytest
import logging


logger = logging.getLogger(__name__)


TAG_PREFIX = 'quay.io/example/builder-test'


@pytest.fixture
def build_dir_and_ee_yml():
    """Fixture to return temporary file maker."""

    def tmp_dir_and_file(ee_contents):
        tmpdir = tempfile.mkdtemp(prefix="ansible-builder-test-")
        with tempfile.NamedTemporaryFile(delete=False, dir=tmpdir) as tempf:
            tempf.write(bytes(ee_contents, "UTF-8"))
        return tmpdir, tempf.name

    return tmp_dir_and_file


def run(args, *a, allow_error=False, **kw):
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

    for i, arg in enumerate(args):
        if not isinstance(arg, str):
            raise pytest.fail(
                f'Argument {arg} in {i} position is not string, args:\n{args}'
            )

    try:
        ret = CompletedProcessProxy(subprocess.run(args, shell=True, *a, **kw))
    except subprocess.CalledProcessError as err:
        if not allow_error:
            # Previously used pytest.fail here, but that missed some error details
            print(
                f"Running {err.cmd} resulted in a non-zero return code: {err.returncode} - stdout: {err.stdout}, stderr: {err.stderr}"
            )
            raise
        err.rc = err.returncode  # lazyily make it look like a CompletedProcessProxy
        return err

    return ret


@pytest.fixture(scope='session', autouse=True)
def cleanup_ee_tags(container_runtime, request):
    def delete_images():
        r = run(f'{container_runtime} images --format="{{{{.Repository}}}}"')
        for image_name in r.stdout.split('\n'):
            from_test = False
            if not image_name:
                pass
            elif image_name.startswith('localhost/{0}'.format(TAG_PREFIX)):  # podman
                from_test = True
            elif image_name.startswith(TAG_PREFIX):  # docker
                from_test = True
            if from_test:
                run(f'{container_runtime} rmi -f {image_name}')
                logger.warning(f'Deleted image {image_name}')

    request.addfinalizer(delete_images)


@pytest.fixture()
def ee_tag(request, container_runtime):
    return '_'.join([
        TAG_PREFIX,
        request.node.name.lower().replace('[', '_').replace(']', '_'),
        str(uuid.uuid4())[:10]
    ])


@pytest.fixture(scope='class')
def ee_tag_class(request, container_runtime):
    return '_'.join([
        TAG_PREFIX,
        request.node.name.lower().replace('[', '_').replace(']', '_'),
        str(uuid.uuid4())[:10]
    ])


class CompletedProcessProxy(object):
    def __init__(self, result):
        self.result = result

    def __getattr__(self, attr):
        return getattr(self.result, attr)


@pytest.fixture()
def cli():
    return run


@pytest.fixture(scope='class')
def cli_class():
    return run


@pytest.fixture(params=['docker', 'podman'], ids=['docker', 'podman'], scope='session')
def container_runtime(request):
    if run(f'{request.param} --version', check=False).returncode == 0:
        return request.param
    else:
        pytest.skip(f'{request.param} runtime not available')
