import subprocess
import pytest


class TestV3:

    def test_ansible_check_is_skipped(self, cli, tmp_path, data_dir, podman_ee_tag):
        """
        Test that the check_ansible script is skipped will NOT cause build failure.
        """
        ee_def = data_dir / 'v3' / 'check_ansible' / 'ee-skip.yml'

        result = cli(
            f'ansible-builder build -c {tmp_path} -f {ee_def} -t {podman_ee_tag} '
            f'--container-runtime=podman -v3'
        )

        assert result.rc == 0

    def test_missing_ansible(self, cli, tmp_path, data_dir, podman_ee_tag):
        """
        Test that the check_ansible script will cause build failure if
        ansible-core is not installed.
        """
        ee_def = data_dir / 'v3' / 'check_ansible' / 'ee-missing-ansible.yml'

        with pytest.raises(subprocess.CalledProcessError) as einfo:
            cli(
                f'ansible-builder build -c {tmp_path} -f {ee_def} -t {podman_ee_tag} '
                f'--container-runtime=podman -v3'
            )

        assert "ERROR - Missing Ansible installation" in einfo.value.stdout

    def test_missing_runner(self, cli, tmp_path, data_dir, podman_ee_tag):
        """
        Test that the check_ansible script will cause build failure if
        ansible-runner is not installed.
        """
        ee_def = data_dir / 'v3' / 'check_ansible' / 'ee-missing-runner.yml'

        with pytest.raises(subprocess.CalledProcessError) as einfo:
            cli(
                f'ansible-builder build -c {tmp_path} -f {ee_def} -t {podman_ee_tag} '
                f'--container-runtime=podman -v3'
            )

        assert "ERROR - Missing Ansible Runner installation" in einfo.value.stdout
