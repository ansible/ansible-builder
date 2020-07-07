import os
import shutil


class PipSteps:
    def __init__(self, containerfile):
        definition = containerfile.definition
        self.steps = []
        if definition.python_requirements_file:
            f = definition.python_requirements_file
            f_name = os.path.basename(f)
            self.steps.append(
                "ADD {} /build/".format(f_name)
            )
            shutil.copy(f, containerfile.build_context)
            self.steps.extend([
                "",
                "RUN pip3 install -r {0}".format(f_name)
            ])

    def __iter__(self):
        return iter(self.steps)
