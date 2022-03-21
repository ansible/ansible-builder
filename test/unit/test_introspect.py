import os

from ansible_builder.introspect import process, process_collection, simple_combine
from ansible_builder.requirements import sanitize_requirements


def test_multiple_collection_metadata(data_dir):

    files = process(data_dir)
    files['python'] = sanitize_requirements(files['python'])
    files['system'] = simple_combine(files['system'])

    assert files == {'python': [
        'pyvcloud>=14,>=18.0.10  # from collection test.metadata,test.reqfile',
        'pytz  # from collection test.reqfile',
        # python-dateutil should appear only once even though referenced in
        # multiple places, once with a dash and another with an underscore in the name.
        'python-dateutil>=2.8.2  # from collection test.reqfile',
        'tacacs-plus  # from collection test.reqfile'
    ], 'system': [
        'subversion [platform:rpm]  # from collection test.bindep',
        'subversion [platform:dpkg]  # from collection test.bindep'
    ]}


def test_single_collection_metadata(data_dir):

    col_path = os.path.join(data_dir, 'ansible_collections', 'test', 'metadata')
    py_reqs, sys_reqs = process_collection(col_path)

    assert py_reqs == ['pyvcloud>=14']
    assert sys_reqs == []
