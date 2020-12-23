import json

import pbr.version
import pkg_resources


version_info = pbr.version.VersionInfo('ansible-builder')
release_string = version_info.release_string()

is_release = None
git_version = None
try:
    _metadata = json.loads(
        pkg_resources.get_distribution('ansible-builder').get_metadata('pbr.json'))
    if _metadata:
        is_release = _metadata['is_release']
        git_version = _metadata['git_version']
except Exception:
    pass
