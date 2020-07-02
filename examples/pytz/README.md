## AWX collection and pytz example

This example demonstrates the use of a collection's python dependency.
You can execute the example by invoking the `run.sh` script.

```
source examples/pytz/run.sh
```

This will start out by deleting the existing build context and image.

Then it runs `ansible-builder build` to re-create these things.

After that, it invokes a playbook from that image which uses the
example playbook.
The example playbook invokes a lookup plugin which requires the
`pytz` and `python-dateutil` libraries, and will fail if those
are not present in the image.

### Build Context

This example produces the Dockerfile:

```
FROM shanemcd/ansible-runner

ADD requirements.yml /build/

RUN ansible-galaxy role install -r /build/requirements.yml --roles-path /usr/share/ansible/roles
RUN ansible-galaxy collection install -r /build/requirements.yml --collections-path /usr/share/ansible/collections
RUN pip3 install -r /usr/share/ansible/collections/ansible_collections/awx/awx/requirements.txt
```

