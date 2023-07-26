import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import uuid
import filelock
import pytest
import yaml


TAG_PREFIX = 'quay.io/example/builder-test'
KEEP_IMAGES = bool(os.environ.get('KEEP_IMAGES', False))

CONTAINER_RUNTIMES = (
    'docker',
    'podman',
)

FOUND_RUNTIMES = set()

GOOD_CONTENT = {'version': 1}

# List of image names indexed by runtime name. E.g., {'podman', ['image1', ...]}
WORKER_IMAGES = {}


# This will be called once for each pytest-xdist worker (-n value).
# The main worker driving the other workers (worker_id is None) will
# have this called last so it will be responsible for the cleanup
# work.
def pytest_sessionfinish(session, exitstatus):
    # pylint: disable=W0613
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    base_tmpfile = os.path.join(tempfile.gettempdir(), "builder_pytest_data_")

    for runtime, images in WORKER_IMAGES.items():
        data_file = pathlib.Path(base_tmpfile + runtime)
        with filelock.FileLock(str(data_file) + ".lock"):
            # Append any images created in this runtime to the data file
            with open(str(data_file), "a") as f:
                f.write("\n".join(images))
                f.write("\n")

    # If we are the main worker thread, we've been called last, so do the cleanup.
    if worker_id is None:
        for runtime in CONTAINER_RUNTIMES:
            data_file = pathlib.Path(base_tmpfile + runtime)
            if data_file.exists():
                for image_name in data_file.read_text().split("\n"):
                    if image_name:
                        delete_image(runtime, image_name)
                data_file.unlink()


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


def pytest_addoption(parser):
    parser.addoption(
        '--run-destructive',
        action='store_true',
        default=False,
        help='Run tests that may be destructive to the host'
    )
    parser.addoption(
        '--skip-runtime',
        choices=CONTAINER_RUNTIMES,
        action='append',
        help='Skip tests for a container runtime engine'
    )


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


@pytest.fixture
def good_exec_env_definition_path(tmp_path):
    path = tmp_path / 'aee'
    path.mkdir()
    path = path / 'execution-env.yml'

    with path.open('w') as outfile:
        yaml.dump(GOOD_CONTENT, outfile)

    return path


@pytest.fixture
def galaxy_requirements_file(tmp_path):

    def _write_file(content=None):
        if content is None:
            content = {}
        path = tmp_path / 'galaxy'
        path.mkdir()
        path = path / 'requirements.yml'

        with path.open('w') as outfile:
            yaml.dump(content, outfile)

        return path

    return _write_file


# This will be called once for every xdist worker session. For more info, see:
# https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html#how-it-works
def pytest_sessionstart(session):
    """Find the available runtimes only once per test session."""
    skip_runtimes = session.config.getoption('--skip-runtime') or []
    for runtime in CONTAINER_RUNTIMES:
        if shutil.which(runtime) and runtime not in skip_runtimes:
            FOUND_RUNTIMES.add(runtime)


def pytest_collection_modifyitems(session, config, items):
    # pylint: disable=W0613
    # mark destructive items as skipped if `--run-destructive` was not specified
    if not config.getoption('--run-destructive'):
        for destructive_item in (i for i in items if any(i.iter_markers(name='destructive'))):
            destructive_item.add_marker(
                pytest.mark.skip(reason='test is potentially destructive to the host (add --run-destructive to allow)')
            )

    # mark serial items as skipped if it looks like we're running with some obvious kinds of parallelism
    numproc = getattr(config.known_args_namespace, 'numprocesses', None)

    if isinstance(numproc, int) and numproc > 1:
        for serial_item in (i for i in items if any(i.iter_markers(name='serial'))):
            serial_item.add_marker(
                pytest.mark.skip(reason='test requires serial execution (add --numprocesses 0 to allow)')
            )


def pytest_generate_tests(metafunc):
    """If a test uses the custom marker ``test_all_runtimes``, generate marks
    for all supported container runtimes. The requires the test to accept
    and use the ``runtime`` argument.

    This also serves to identify the runtime being tested through the pytest
    output by appending "[<runtime>]" to the test name.

    Based on examples from https://docs.pytest.org/en/latest/example/parametrize.html.
    """
    for mark in getattr(metafunc.function, 'pytestmark', []):
        if getattr(mark, 'name', '') == 'test_all_runtimes':
            args = tuple(
                pytest.param(
                    runtime,
                    marks=pytest.mark.skipif(
                        runtime not in FOUND_RUNTIMES,
                        reason=f'{runtime} skipped or not found'),
                ) for runtime in CONTAINER_RUNTIMES
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
    # pylint: disable=W1510
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
        raise Exception(f'Image cleanup failed (rc={r.rc}):\n{r.stdout}\n{r.stderr}')


@pytest.fixture
def podman_ee_tag(request):
    image_name = gen_image_name(request)
    WORKER_IMAGES.setdefault('podman', [])
    WORKER_IMAGES['podman'].append(image_name)
    yield image_name


@pytest.fixture
@pytest.mark.test_all_runtimes
def ee_tag(request, runtime):
    image_name = gen_image_name(request)
    WORKER_IMAGES.setdefault(runtime, [])
    WORKER_IMAGES[runtime].append(image_name)
    yield image_name


class CompletedProcessProxy:
    def __init__(self, result):
        self.rc = 0
        self.result = result

    def __getattr__(self, attr):
        return getattr(self.result, attr)


@pytest.fixture
def cli():
    return run


@pytest.fixture
def source_file(tmp_path):
    source = tmp_path / 'bar.txt'
    with open(source, 'w') as f:
        f.write('foo\nbar\n')
    return source


@pytest.fixture
def dest_file(tmp_path, source_file):
    # pylint: disable=W0621
    '''Returns a file that has been copied from source file'''
    dest = tmp_path / 'foo.txt'
    shutil.copy2(source_file, dest)
    return dest
