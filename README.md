# UTXO Prometheus Exporter

A [Prometheus] exporter for UTXO blockchain nodes written in python and packaged for running as a container.

A rudimentary Grafana [dashboard] is available in the [`dashboard/bitcoin-grafana.json`](dashboard/bitcoin-grafana.json)
file.

The main script is a modified version of [`bitcoin-monitor.py`][source-gist], updated to remove the need for the
`bitcoin-cli` binary, packaged into a [Docker image][docker-image], and expanded to export additional metrics.

[Prometheus]: https://github.com/prometheus/prometheus
[docker-image]: https://hub.docker.com/r/jvstein/bitcoin-prometheus-exporter

[source-gist]: https://gist.github.com/ageis/a0623ae6ec9cfc72e5cb6bde5754ab1f
[python-bitcoinlib]: https://github.com/petertodd/python-bitcoinlib
[dashboard]: https://grafana.com/grafana/dashboards/11274

## Usage

### Run without docker

1. You need to have python >= 3.8 and [pipenv]
2. Install dependencies:

    pipenv install

3. Load the environment:

    pipenv shell

4. Run the script:

    UTXO_NODE_RPC_HOST=bitcoin-node-address \
    UTXO_NODE_RPC_USER=rpc-username \
    UTXO_NODE_RPC_PASSWORD=rpc-password \
    python3 utxo_prometheus_exporter.py

[pipenv]: https://pipenv.pypa.io/en/latest/

### Run with docker
```sh
docker run \
    --name=utxo-prometheus-exporter \
    -p 9332:9332 \
    -e UTXO_NODE_BLOCKCHAIN_NAME=bitcoin
    -e UTXO_NODE_RPC_HOST=bitcoin-node \
    -e UTXO_NODE_RPC_USER=alice \
    -e UTXO_NODE_RPC_PASSWORD=DONT_USE_THIS_YOU_WILL_GET_ROBBED_8ak1gI25KFTvjovL3gAM967mies3E= \
    santiment/utxo-prometheus-exporter:latest
```

### Run in Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: litecoin-prometheus-exporter
  labels:
    app: litecoin-prometheus-exporter
spec:
  selector:
    matchLabels:
      app: litecoin-prometheus-exporter
  replicas: 1
  template:
    metadata:
      labels:
        app: litecoin-prometheus-exporter
      annotations:
        prometheus.io/scrape: 'true'
        prometheus.io/port:   '9335'
    spec:
      containers:
        - name: litecoin-prometheus-exporter
          image: santiment/utxo-prometheus-exporter:latest
          imagePullPolicy: Always
          env:
            - name: UTXO_NODE_BLOCKCHAIN_NAME
              value: litecoin
            - name: UTXO_NODE_RPC_HOST
              value: "litecoin-node.default"
            - name: UTXO_NODE_RPC_PORT
              value: "9332"
            - name: UTXO_NODE_RPC_USER
              value: "rpc-user"
            - name: UTXO_NODE_RPC_PASSWORD
              value: "rpc-password"
            - name: REFRESH_SECONDS
              value: "1"
            - name: METRICS_PORT
              value: "9335"
```

## Basic Testing
There's a [`docker-compose.yml`](docker-compose.yml) file in the repository that references a test bitcoin node. To test changes to the exporter in docker, run the following commands.

```
docker-compose down
docker-compose up --build
```

If you see a lot of `ConnectionRefusedError` errors, run `chmod og+r test-bitcoin.conf`.

# [Change Log](CHANGELOG.md)
See the [`CHANGELOG.md`](CHANGELOG.md) file for changes.
