import os
import shutil


class PipSteps:
    def __new__(cls, containerfile):
        definition = containerfile.definition
        steps = []
        if definition.python_requirements_file:
            f = definition.python_requirements_file
            f_name = os.path.basename(f)
            steps.append(
                "ADD {} /build/".format(f_name)
            )
            shutil.copy(f, containerfile.build_context)
            steps.extend([
                "",
                "RUN pip3 install -r {0}".format(f_name)
            ])

        return steps
