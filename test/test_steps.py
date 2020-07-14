import pytest
import textwrap

from ansible_builder.steps import AdditionalBuildSteps, PipSteps


def test_steps_for_collection_dependencies():
    assert list(PipSteps(None, [
        'test/metadata/my-requirements.txt',
        'test/reqfile/requirements.txt'
    ])) == [
        '\n'.join([
            'RUN pip3 install \\',
            '    -r /usr/share/ansible/collections/ansible_collections/test/metadata/my-requirements.txt \\',
            '    -r /usr/share/ansible/collections/ansible_collections/test/reqfile/requirements.txt'
        ])
    ]


@pytest.mark.parametrize('verb', ['prepend', 'append'])
def test_additional_build_steps(verb):
    additional_build_steps = {
        'prepend': ["RUN echo This is the prepend test", "RUN whoami"],
        'append': textwrap.dedent("""
        RUN echo This is the append test
        RUN whoami
        """)
    }
    steps = AdditionalBuildSteps(additional_build_steps[verb])

    assert len(list(steps)) == 2
