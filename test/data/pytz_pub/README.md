## Publishing and pulling image

First, the example `examples/pytz` was ran.
After that, the image was published via:

```
docker tag awx-awx alancoding/awx-awx
docker push alancoding/awx-awx
```

This example uses the published version of the execution environment,
from Dockerhub in this case.

See that defined in `env/settings`

Note that this folder does not contain anything related to building
the execution environment.
This only contains the ansible-runner project folder, which is the point.
