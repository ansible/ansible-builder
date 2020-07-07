import os
import shutil

from .. import constants


class GalaxySteps:
    def __init__(self, containerfile):
        self.definition = containerfile.definition
        self.steps = []
        if self.definition.galaxy_requirements_file:
            f = self.definition.galaxy_requirements_file
            f_name = os.path.basename(f)
            self.steps.append(
                "ADD {} /build/".format(f_name)
            )
            shutil.copy(f, containerfile.build_context)
            self.steps.extend([
                "",
                "RUN ansible-galaxy role install -r /build/{0} --roles-path {1}".format(
                    f_name, constants.base_roles_path),
                "RUN ansible-galaxy collection install -r /build/{0} --collections-path {1}".format(
                    f_name, constants.base_collections_path)
            ])
            self.steps.extend(
                self.collection_python_steps()
            )

    def __iter__(self):
        return iter(self.steps)

    def collection_python_steps(self):
        steps = []
        collection_deps = self.definition.collection_dependencies()
        if collection_deps['python']:
            steps.extend([
                "",
                "WORKDIR {0}".format(os.path.join(
                    constants.base_collections_path, 'ansible_collections'
                ))
            ])
            steps.append(
                "RUN pip3 install \\\n    -r {0}".format(
                    ' \\\n    -r '.join(collection_deps['python'])
                )
            )
        return steps
