import os
import subprocess

import tempfile
import uuid

import pytest
import logging

logger = logging.getLogger(__name__)

TAG_PREFIX = 'quay.io/example/builder-test'
KEEP_IMAGES = bool(os.environ.get('KEEP_IMAGES', False))


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

    ret.rc = ret.result.returncode

    return ret


def gen_image_name(request):
    return '_'.join([
        TAG_PREFIX,
        request.node.name.lower().replace('[', '_').replace(']', '_'),
        str(uuid.uuid4())[:10]
    ])


def delete_image(container_runtime, image_name):
    if KEEP_IMAGES:
        return
    # delete given image, if the test happened to make one
    # allow error in case that image was not created
    r = run(f'{container_runtime} rmi -f {image_name}', allow_error=True)
    if r.rc != 0:
        if 'no such image' in r.stdout or 'no such image' in r.stderr:
            return
        else:
            raise Exception(f'Teardown failed (rc={r.rc}):\n{r.stdout}\n{r.stderr}')


@pytest.fixture()
def ee_tag(request, container_runtime):
    image_name = gen_image_name(request)
    yield image_name
    delete_image(container_runtime, image_name)


@pytest.fixture(scope='class')
def ee_tag_class(request, container_runtime):
    image_name = gen_image_name(request)
    yield image_name
    delete_image(container_runtime, image_name)


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
