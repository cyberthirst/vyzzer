## On host

### Setup virtual environment
- the process of installation isn't yet streamlined and contains some issues. The following steps are known to be working against ubuntu lts
- tested against Python 3.10.10 venvs
- installation of the requirements.txt is a bit problematic due to compilation of protobuf-mutator
- `pip install -r temp_requirements.txt` which doesn't include a problematic libprotobuf-mutator package
- install the `libprotobuf-mutator` package manually
  - we temporarily resolved the problem by manually cloning `https://github.com/google/atheris.git` and manually installing ontents of `atheris/contrib/libprotobuf_mutator
    - the install fails but we modified its `setup.py` with
```
     ["-c", "opt", 
         "--repo_env=CC=clang",
         "--repo_env=CXX=clang++",
         "--cxxopt=-std=c++17",
         "--cxxopt=-include", "--cxxopt=cstdint",
         "--cxxopt=-include", "--cxxopt=stdint.h",
         "//:_mutator.so"],
```


### Periphery

To run the set-up localy it's required to run database and AMQ
instances.
Running DB:

```bash
docker run -d -p 27017:27017 mongo
```

For each `runner`, there must be a separate AMQ

AMQ:

```bash
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:management
docker run -d -p 5673:5672 -p 15673:15672 rabbitmq:management
```

So now the database and AMQ services are allowed by `localhost:27017` and `localhost:5672` respectively.
The periphery can be run outside of docker, although normally multiple instances of AMQ are required.

### Configuration

Since the periphery are run we need to put according configurations to `config.yml` file:

```yaml
compilers:
  - name: adder
    queue:
      host: localhost
      port: 5672
    exec_params:
      optimization: "gas"
  - name: nagini
    queue:
      host: localhost
      port: 5673
    exec_params:
      venom: False
db:
  host: localhost
  port: 27017
input_strategies: [1]
verbosity: DEBUG
extra_flags: ['enable_decimals']
```

### Running the Runner service

The differential fuzzing might require having separate dependencies to run (`vyper`&`titanoboa` versions).
Run each set of `runners` in a different virtual environment.

#### Example environment one

```bash
pip install -r requirements_adder.txt
```

```bash
export PYTHONPATH=$(pwd)
SERVICE_NAME=adder python fuzz/runners/runner_diff.py
```

#### Example environment two

```bash
pip install -r requirements_nagini.txt
```

```bash
export PYTHONPATH=$(pwd)
SERVICE_NAME=nagini python fuzz/runners/runner_diff.py
```

### Running the Generator service

The `generator` is anchored to one of the `vyper` versions in a differential fuzzing set-up.
The `generator` service must run in the environment with the `vyper` version that `converter` is adapted to, it can be run in the same virtual environment as one of `runner` services (depending on the anchored version for cross-version).

Compile the proto file:

```bash
protoc  --python_out=./ ./vyperProto.proto
```

Since all dependencies are installed the services can be run:

```bash
export PYTHONPATH=$(pwd)
python fuzz/generators/run_diff.py
```

### Running the Verifier service

Does not depend on the `vyper` or `titanoboa` versions, but must have dependencies installed.

```bash
export PYTHONPATH=$(pwd)
python fuzz/verifiers/simple_verifier.py
```
