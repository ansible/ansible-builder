from ansible_builder.steps import PipSteps


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
