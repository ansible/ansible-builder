import os
import shutil

from .. import constants


class GalaxySteps:
    def __new__(cls, containerfile):
        definition = containerfile.definition
        steps = []
        if definition.galaxy_requirements_file:
            f = definition.galaxy_requirements_file
            f_name = os.path.basename(f)
            steps.append(
                "ADD {} /build/".format(f_name)
            )
            shutil.copy(f, containerfile.build_context)
            steps.extend([
                "",
                "RUN ansible-galaxy role install -r /build/{0} --roles-path {1}".format(
                    f_name, constants.base_roles_path),
                "RUN ansible-galaxy collection install -r /build/{0} --collections-path {1}".format(
                    f_name, constants.base_collections_path)
            ])
            steps.extend(
                cls.collection_python_steps(containerfile.definition)
            )
        return steps

    @staticmethod
    def collection_python_steps(user_definition):
        steps = []
        collection_deps = user_definition.collection_dependencies()
        if collection_deps['python']:
            steps.extend([
                "",
                "WORKDIR {0}".format(os.path.join(
                    constants.base_collections_path, 'ansible_collections'
                ))
            ])
            steps.append(
                "RUN pip3 install && \\\n    -r {0}".format(
                    ' && \\\n    -r '.join(collection_deps['python'])
                )
            )
        return steps
