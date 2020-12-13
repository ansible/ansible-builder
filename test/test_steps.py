import pytest
import textwrap

from ansible_builder.steps import AdditionalBuildSteps, PipInstallSteps, BindepSteps


def test_steps_for_collection_dependencies():
    assert list(PipInstallSteps('requirements.txt')) == [
        'ADD requirements.txt /build/',
        'COPY --from=builder /output/wheels /output/wheels',
        'RUN pip3 install --cache-dir=/output/wheels -r /build/requirements.txt'
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
    assert list(BindepSteps('bindep_runtime_output.txt')) == [
        'ADD bindep_runtime_output.txt /build/',
        'RUN dnf -y install $(cat /build/bindep_runtime_output.txt)'
    ]
