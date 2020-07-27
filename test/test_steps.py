import pytest
import textwrap

from ansible_builder.steps import AdditionalBuildSteps, PipSteps, BindepSteps


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

def test_system_steps():
    assert list(BindepSteps(
        'bindep.txt'
    )) == [
        'ADD bindep.txt /build/',
        'RUN pip3 install bindep',
        'RUN yum -y install $(bindep -q -f /build/bindep.txt)'
    ]
