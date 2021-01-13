import os
import subprocess
from pathlib import Path
from glob import glob
import shutil

import tempfile
import uuid

import pytest
import logging


logger = logging.getLogger(__name__)


TAG_PREFIX = 'quay.io/example/builder-test'
LOCK_DIR = '/tmp/ansible_builder_tests'


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


@pytest.fixture(scope='session', autouse=True)
def cleanup_ee_tags(container_runtime, request):
    pid = os.getpid()

    try:
        os.mkdir(LOCK_DIR)
    except FileExistsError:
        pass
    except Exception:
        raise

    start_file = f'{LOCK_DIR}/start_{pid}.txt'
    Path(start_file).touch()

    try:
        yield
    finally:
        start_glob = f'{LOCK_DIR}/start_*.txt'
        end_glob = f'{LOCK_DIR}/end_*.txt'

        is_final = bool(len(glob(start_glob)) <= len(glob(end_glob)) + 1)

        end_file = f'{LOCK_DIR}/end_{pid}.txt'
        Path(end_file).touch()

        if is_final:
            shutil.rmtree(LOCK_DIR)
            list_cmd = (
                f'{container_runtime} images --format="{{{{.Repository}}}}"'
                f' | grep "{TAG_PREFIX}" --color=never'
            )
            cmd = f'{container_runtime} rmi -f $({list_cmd})'
            r = run(cmd, allow_error=True)
            if r.rc != 0:
                listing = run(list_cmd, allow_error=True)
                if listing.stdout.strip() != '':
                    raise Exception(f'Teardown failed (rc={r.rc}):\n{r.stdout}\n{r.stderr}')
            print(f'Deleted images, cmd:\n{cmd}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}')


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
