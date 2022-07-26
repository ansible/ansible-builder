import pytest
import shutil
import subprocess
import uuid

from pathlib import Path

from ansible_builder.policies import RejectAll, IgnoreAll


# All tests in this file require podman to be installed. Skip them all if it isn't.
pytestmark = pytest.mark.skipif(shutil.which("podman") is None, reason="podman not installed")

RUN_UUID = str(uuid.uuid4())
USER_POLICY_PATH = '~/.config/containers/policy.json'
BACKUP_POLICY_PATH = f'~/.config/containers/policy.json.{RUN_UUID}'
USER_REGISTRIES_PATH = '~/.config/containers/registries.conf'
BACKUP_REGISTRIES_PATH = f'~/.config/containers/registries.conf.{RUN_UUID}'


@pytest.mark.serial
class TestPolicies:
    """
    All tests within this class must run serially since they all make use of
    the test user's policy.json file which is acting as our system-level
    podman policy file. The user's registries.conf is also altered.
    """

    @classmethod
    def setup_class(cls):
        """
        These tests will make use of "system" podman files (USER_POLICY_PATH).
        In order to assist developers with local testing, we'll move this file
        out of the way (BACKUP_POLICY_PATH) and restore it during test teardown.

        Our pulp-based test registry does not use secure connections, so we must
        modify our registries.conf file so that podman commands will not fail.
        The original registries.conf file should be restored during teardown.

        After all tests are done, remove images downloaded from pulp repo and
        dangling (<none>) images.
        """
        user_policy = Path(USER_POLICY_PATH).expanduser()
        if user_policy.exists():
            target = Path(BACKUP_POLICY_PATH).expanduser()
            user_policy.rename(target)

        user_registries = Path(USER_REGISTRIES_PATH).expanduser()
        if user_registries.exists():
            target = Path(BACKUP_REGISTRIES_PATH).expanduser()
            user_registries.rename(target)

        data = '[[registry]]\nlocation="localhost:8080"\ninsecure=true\n'
        conf = Path(USER_REGISTRIES_PATH).expanduser()
        conf.parent.mkdir(parents=True, exist_ok=True)
        conf.write_text(data)

        try:
            cmd = 'podman image prune --force'
            subprocess.run(cmd.split())
            cmd = 'podman rmi localhost:8080/testrepo/ansible-builder-rhel8:latest'
            subprocess.run(cmd.split())
        except Exception:
            pass

    @classmethod
    def teardown_class(cls):
        """
        Restore the user policy.json file.
        """
        renamed_policy = Path(BACKUP_POLICY_PATH).expanduser()
        if renamed_policy.exists():
            target = Path(USER_POLICY_PATH).expanduser()
            renamed_policy.rename(target)

        renamed_registries = Path(BACKUP_REGISTRIES_PATH).expanduser()
        if renamed_registries.exists():
            target = Path(USER_REGISTRIES_PATH).expanduser()
            renamed_registries.rename(target)

    def write_policy(self, data):
        policy = Path(USER_POLICY_PATH).expanduser()
        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text(data)

    def test_ignore_all(self, cli, tmp_path, data_dir, podman_ee_tag):
        """
        Test that ignore_all policy will work with a system level policy that
        rejects everything by default.

        To verify that we actually do not do image signature validation with
        ignore_all, we use an execution environment file that would normally
        fail with signature validation.
        """
        ee_def = data_dir / 'v2' / 'sig_req' / 'ee-no-orig.yml'

        # Make a system policy that rejects everything.
        policy = RejectAll()
        policy.write_policy(str(Path(USER_POLICY_PATH).expanduser()))

        # Use the ignore_all policy to override the system policy.
        result = cli(
            f'ansible-builder build -c {tmp_path} -f {ee_def} -t {podman_ee_tag} '
            f'--container-runtime=podman --container-policy=ignore_all -v3'
        )

        assert result.rc == 0
        assert f"--signature-policy={tmp_path}/policy.json" in result.stdout
        assert f"Complete! The build context can be found at: {tmp_path}" in result.stdout

    def test_system(self, cli, tmp_path, data_dir, podman_ee_tag):
        """
        Test that a system level policy.json file will be used with the
        `system` policy.

        Expect `--pull-always` to be present in the podman command and that
        a policy.json file is not present with the podman command.
        """
        ee_def = data_dir / 'v2' / 'sig_req' / 'ee-good.yml'

        # Make a system policy that accepts everything.
        policy = IgnoreAll()
        policy.write_policy(str(Path(USER_POLICY_PATH).expanduser()))

        # Use the system policy
        result = cli(
            f'ansible-builder build -c {tmp_path} -f {ee_def} -t {podman_ee_tag} '
            f'--container-runtime=podman --container-policy=system -v3'
        )

        assert result.rc == 0
        assert "--pull-always" in result.stdout
        assert f"--signature-policy={tmp_path}/policy.json" not in result.stdout
        assert f"Complete! The build context can be found at: {tmp_path}" in result.stdout

    def test_signature_required_success(self, cli, tmp_path, data_dir, podman_ee_tag):
        """
        Test that signed images are validated when using the signature_required policy.

        ee-good.yml is valid and should pass with the RPM-GPG-KEY-redhat-release keyring.
        """
        ee_def = data_dir / 'v2' / 'sig_req' / 'ee-good.yml'
        keyring = data_dir / 'v2' / 'RPM-GPG-KEY-redhat-release'
        result = cli(
            f'ansible-builder build -c {tmp_path} -f {ee_def} -t {podman_ee_tag} '
            f'--container-runtime=podman --container-policy=signature_required --container-keyring={keyring} -v3'
        )

        assert result.rc == 0
        assert "--pull-always" in result.stdout
        assert f"--signature-policy={tmp_path}/policy.json" in result.stdout
        assert "Getting image source signatures" in result.stdout
        assert "Checking if image destination supports signatures" in result.stdout
        assert f"Complete! The build context can be found at: {tmp_path}" in result.stdout

    def test_signature_required_fail(self, cli, tmp_path, data_dir, podman_ee_tag):
        """
        Test that failure to validate a signed image will fail.

        We force failure by supplying an empty keyring.
        """
        ee_def = data_dir / 'v2' / 'sig_req' / 'ee-good.yml'
        keyring = data_dir / 'v2' / 'invalid-keyring'

        with pytest.raises(subprocess.CalledProcessError) as einfo:
            cli(
                f'ansible-builder build -c {tmp_path} -f {ee_def} -t {podman_ee_tag} '
                f'--container-runtime=podman --container-policy=signature_required --container-keyring={keyring} -v3'
            )

        assert "Source image rejected: None of the signatures were accepted" in einfo.value.stdout

    def test_signature_required_no_orig(self, cli, tmp_path, data_dir, podman_ee_tag):
        """
        Test that using a signed image, but not specifying the original image name, fails.

        ee-no-orig.yml is identical to ee-good.yml, except the signature_original_name is missing on an image.
        """
        ee_def = data_dir / 'v2' / 'sig_req' / 'ee-no-orig.yml'
        keyring = data_dir / 'v2' / 'invalid-keyring'

        with pytest.raises(subprocess.CalledProcessError) as einfo:
            cli(
                f'ansible-builder build -c {tmp_path} -f {ee_def} -t {podman_ee_tag} '
                f'--container-runtime=podman --container-policy=signature_required --container-keyring={keyring} -v3'
            )

        assert "Source image rejected: None of the signatures were accepted" in einfo.value.stdout
