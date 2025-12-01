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

# run pytest with boardfarm:
pytest --log-level=DEBUG --log-cli-level=DEBUG  --html=report.html --self-contained-html --board-name prplos-docker-1 --env-config ./bf_config/boardfarm_env_example.json --inventory-config ./bf_config/boardfarm_config_example.json --legacy  --save-console-logs ./logs/ -k "UC12348Main" 
```


