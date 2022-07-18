import os
import pathlib
import pytest
import re
import shutil
import subprocess
import uuid
import yaml


TAG_PREFIX = 'quay.io/example/builder-test'
KEEP_IMAGES = bool(os.environ.get('KEEP_IMAGES', False))

CONTAINER_RUNTIMES = (
    'docker',
    'podman',
)


@pytest.fixture(autouse=True)
def do_not_run_commands(request, mocker):
    if 'run_command' in request.keywords:
        yield
        return
    cmd_mock = mocker.MagicMock(return_value=[1, [
        'python:', '  foo: []', 'system: {}',
    ]])
    mocker.patch('ansible_builder.main.run_command', new=cmd_mock)
    yield cmd_mock


@pytest.fixture(scope='session')
def data_dir():
    return pathlib.Path(pathlib.Path(__file__).parent).joinpath('data')


@pytest.fixture
def exec_env_definition_file(tmp_path):

    def _write_file(content=None):
        path = tmp_path / 'aee'
        path.mkdir()
        path = path / 'execution-env.yml'

        write_str = {}
        if isinstance(content, dict):
            write_str = yaml.dump(content)
        elif isinstance(content, str):
            write_str = content

        path.write_text(write_str)

        return path

    return _write_file


good_content = {'version': 1}


@pytest.fixture
def good_exec_env_definition_path(tmp_path):
    path = tmp_path / 'aee'
    path.mkdir()
    path = path / 'execution-env.yml'

    with path.open('w') as outfile:
        yaml.dump(good_content, outfile)

    return path


@pytest.fixture
def galaxy_requirements_file(tmp_path):

    def _write_file(content={}):
        path = tmp_path / 'galaxy'
        path.mkdir()
        path = path / 'requirements.yml'

        with path.open('w') as outfile:
            yaml.dump(content, outfile)

        return path

    return _write_file


def pytest_generate_tests(metafunc):
    """If a test uses the custom marker ``test_all_runtimes``, generate marks
    for all supported container runtimes. The requires the test to accept
    and use the ``runtime`` argument.

    Based on examples from https://docs.pytest.org/en/latest/example/parametrize.html.
    """

    for mark in getattr(metafunc.function, 'pytestmark', []):
        if getattr(mark, 'name', '') == 'test_all_runtimes':
            args = tuple(
                pytest.param(
                    runtime,
                    marks=pytest.mark.skipif(
                        shutil.which(runtime) is None,
                        reason=f'{runtime} is not installed',
                    ),
                )
                for runtime in CONTAINER_RUNTIMES
            )
            metafunc.parametrize('runtime', args)
            break


@pytest.fixture
def build_dir_and_ee_yml(tmp_path):
    """Fixture to return temporary file maker."""

    def tmp_dir_and_file(ee_contents):
        tmp_file = tmp_path / 'ee.txt'
        tmp_file.write_text(ee_contents)

        return tmp_path, tmp_file

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
            print(f"Running following command resulted in a non-zero return code: {err.returncode}")
            print(err.cmd)
            print('stdout:')
            print(err.stdout)
            print('stderr:')
            print(err.stderr)
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


@pytest.mark.test_all_runtimes
def delete_image(runtime, image_name):
    if KEEP_IMAGES:
        return
    # delete given image, if the test happened to make one
    # allow error in case that image was not created
    regexp = re.compile(r'(no such image)|(image not known)|(image is in use by a container)', re.IGNORECASE)
    r = run(f'{runtime} rmi -f {image_name}', allow_error=True)
    if r.rc != 0:
        if regexp.search(r.stdout) or regexp.search(r.stderr):
            return
        else:
            raise Exception(f'Teardown failed (rc={r.rc}):\n{r.stdout}\n{r.stderr}')


@pytest.fixture
def podman_ee_tag(request):
    image_name = gen_image_name(request)
    yield image_name
    delete_image('podman', image_name)


@pytest.fixture
@pytest.mark.test_all_runtimes
def ee_tag(request, runtime):
    image_name = gen_image_name(request)
    yield image_name
    delete_image(runtime, image_name)


class CompletedProcessProxy(object):
    def __init__(self, result):
        self.result = result

    def __getattr__(self, attr):
        return getattr(self.result, attr)


@pytest.fixture
def cli():
    return run
