# Basic setup to demonstrate Baordfarm and Boardfarm-pytest

## Configuration
The configurations used here can be found in [](./bf_config/) and [](./raikou/)

## Demo flow:
Instantiate the networked components with raikou:
```shell
cd raikou
docker compose up -d --build
```

Wait for all the components to be fully up and running

Check for instance the state of the CPE:
```shell
docker exec -it cpe ash

#inside the container, to get an overview of the environment:
cat etc/environment
```

open a new terminal at the root of the project and start the python venv
(assuming this has been already installed)

```shell
source .venv-3.12/bin/activate

# install Boardfarm if not already the case:
uv pip install boardfarm3[pytest,docsis]
# or if you want to install from local directory:
uv pip install <path to boardfarm directory> -e

# run boardfarm, to get to the boardfarm interactive menu:
boardfarm --board-name  prplos-docker-1 --env-config ./bf_config/boardfarm_env_example.json --inventory-config ./bf_config/boardfarm_config_example.json  --save-console-logs ./logs/ --legacy
```

with boardfarm running, access the genie acs ui:
[http://locahost:300](http://localhost:3000)

the cpe ui can be found at:
[http://192.168.1.1](http://192.168.1.1)

With the following Firefox Manual Proxy Configuration:
SOCKS Host: localhost (or 127.0.0.1)
Port: 8002
Select: SOCKS v5
Check: "Proxy DNS when using SOCKS v5"


```shell
# run pytest with boardfarm:
pytest --log-level=DEBUG --log-cli-level=DEBUG  --html=report.html --self-contained-html --board-name prplos-docker-1 --env-config ./bf_config/boardfarm_env_example.json --inventory-config ./bf_config/boardfarm_config_example.json --legacy  --save-console-logs ./logs/ tests/test_debug_steps.py
```

