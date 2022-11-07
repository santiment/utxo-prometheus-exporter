#!/usr/bin/env python3

# LICENSE information from upstream
# bitcoind-monitor.py
#
# An exporter for Prometheus and Bitcoin Core.
#
# Copyright 2018 Kevin M. Gallagher
# Copyright 2019,2020 Jeff Stein
#
# Published at https://github.com/jvstein/bitcoin-prometheus-exporter
# Licensed under BSD 3-clause (see LICENSE).
#
# Dependency licenses (retrieved 2020-05-31):
#   prometheus_client: Apache 2.0
#   python-bitcoinlib: LGPLv3
#   riprova: MIT

import json
import logging
import time
import os
import signal
import sys
import socket
from datetime import datetime
from functools import lru_cache
from typing import Any
from typing import Dict
from typing import List
from typing import Union
from typing import Callable
from wsgiref.simple_server import make_server

import riprova

from bitcoin.rpc import JSONRPCError, InWarmupError, Proxy
from prometheus_client import make_wsgi_app

from prometheus_metrics import *
from config import *

logger = logging.getLogger("utxo-prometheus-exporter")

RETRY_EXCEPTIONS = (InWarmupError, ConnectionError, socket.timeout)

RpcResult = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

def on_retry(err: Exception, next_try: float) -> None:
    err_type = type(err)
    exception_name = err_type.__module__ + "." + err_type.__name__
    EXPORTER_ERRORS.labels(**{"type": exception_name, "blockchain": UTXO_NODE_BLOCKCHAIN_NAME}).inc()
    logger.error("Retry after exception %s: %s", exception_name, err)


def error_evaluator(e: Exception) -> bool:
    return isinstance(e, RETRY_EXCEPTIONS)


@lru_cache(maxsize=1)
def rpc_client_factory():
    # Configuration is done in this order of precedence:
    #   - Explicit config file.
    #   - UTXO_NODE_RPC_USER and UTXO_NODE_RPC_PASSWORD environment variables.
    #   - Default bitcoin config file (as handled by Proxy.__init__).
    use_conf = (
        (UTXO_NODE_CONF_PATH is not None)
        or (UTXO_NODE_RPC_USER is None)
        or (UTXO_NODE_RPC_PASSWORD is None)
    )

    if use_conf:
        logger.info("Using config file: %s", UTXO_NODE_CONF_PATH or "<default>")
        return lambda: Proxy(btc_conf_file=UTXO_NODE_CONF_PATH, timeout=TIMEOUT)
    else:
        host = UTXO_NODE_RPC_HOST
        host = "{}:{}@{}".format(UTXO_NODE_RPC_USER, UTXO_NODE_RPC_PASSWORD, host)
        if UTXO_NODE_RPC_PORT:
            host = "{}:{}".format(host, UTXO_NODE_RPC_PORT)
        service_url = "{}://{}".format(UTXO_NODE_RPC_SCHEME, host)
        logger.info("Using environment configuration")
        return lambda: Proxy(service_url=service_url, timeout=TIMEOUT)


def rpc_client():
    return rpc_client_factory()()


@riprova.retry(
    timeout=TIMEOUT,
    backoff=riprova.ExponentialBackOff(),
    on_retry=on_retry,
    error_evaluator=error_evaluator,
)
def exec_rpc_call(*args) -> RpcResult:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("RPC call: " + " ".join(str(a) for a in args))

    result = rpc_client().call(*args)

    logger.debug("Result:   %s", result)
    return result


@lru_cache(maxsize=1)
def getblockstats(block_hash: str):
    try:
        block = exec_rpc_call(
            "getblockstats",
            block_hash,
            ["total_size", "total_weight", "totalfee", "txs", "height", "ins", "outs", "total_out"],
        )
    except Exception:
        logger.exception("Failed to retrieve block " + block_hash + " statistics from node.")
        return None
    return block

def do_smartfee(num_blocks: int) -> None:
    smartfee = exec_rpc_call("estimatesmartfee", num_blocks).get("feerate")
    if smartfee is not None:
        gauge = smartfee_gauge(num_blocks)
        gauge.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(smartfee)


def do_hashps_gauge(num_blocks: int) -> None:
    hps = float(exec_rpc_call("getnetworkhashps", num_blocks))
    if hps is not None:
        gauge = hashps_gauge(num_blocks)
        gauge.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(hps)


def sigterm_handler(signal, frame) -> None:
    logger.critical("Received SIGTERM. Exiting.")
    sys.exit(0)

def exception_count(e: Exception) -> None:
    err_type = type(e)
    exception_name = err_type.__module__ + "." + err_type.__name__
    EXPORTER_ERRORS.labels(**{"type": exception_name, "blockchain": UTXO_NODE_BLOCKCHAIN_NAME}).inc()


def fetch_uptime() -> None:
    uptime = exec_rpc_call("uptime")
    if uptime is not None:
        UTXO_NODE_UPTIME.labels(blockchain=f"{UTXO_NODE_BLOCKCHAIN_NAME}").set(uptime)

def fetch_meminfo() -> None:
    meminfo = exec_rpc_call("getmemoryinfo", "stats")["locked"]
    if meminfo is not None:
        UTXO_NODE_MEMINFO_USED.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(meminfo["used"])
        UTXO_NODE_MEMINFO_FREE.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(meminfo["free"])
        UTXO_NODE_MEMINFO_TOTAL.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(meminfo["total"])
        UTXO_NODE_MEMINFO_LOCKED.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(meminfo["locked"])
        UTXO_NODE_MEMINFO_CHUNKS_USED.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(meminfo["chunks_used"])
        UTXO_NODE_MEMINFO_CHUNKS_FREE.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(meminfo["chunks_free"])

def fetch_blockchaininfo() -> None:
    blockchaininfo = exec_rpc_call("getblockchaininfo")
    if blockchaininfo is not None:
        UTXO_NODE_BLOCKS.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(blockchaininfo["blocks"])
        UTXO_NODE_DIFFICULTY.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(blockchaininfo["difficulty"])
        UTXO_NODE_SIZE_ON_DISK.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(blockchaininfo["size_on_disk"])
        UTXO_NODE_VERIFICATION_PROGRESS.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(
            blockchaininfo["verificationprogress"]
        )

def fetch_blockstats() -> None:
    blockchaininfo = exec_rpc_call("getblockchaininfo")
    if blockchaininfo is not None:
        latest_blockstats = getblockstats(str(blockchaininfo["bestblockhash"]))
        if latest_blockstats is not None:
            UTXO_NODE_LATEST_BLOCK_SIZE.labels(
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(latest_blockstats["total_size"])
            UTXO_NODE_LATEST_BLOCK_TXS.labels(
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(latest_blockstats["txs"])
            UTXO_NODE_LATEST_BLOCK_HEIGHT.labels(
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(latest_blockstats["height"])
            UTXO_NODE_LATEST_BLOCK_WEIGHT.labels(
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(latest_blockstats["total_weight"])
            UTXO_NODE_LATEST_BLOCK_INPUTS.labels(
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(latest_blockstats["ins"])
            UTXO_NODE_LATEST_BLOCK_OUTPUTS.labels(
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(latest_blockstats["outs"])
            UTXO_NODE_LATEST_BLOCK_VALUE.labels(
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(latest_blockstats["total_out"] / SATS_PER_COIN)
            UTXO_NODE_LATEST_BLOCK_FEE.labels(
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(latest_blockstats["totalfee"] / SATS_PER_COIN)

def fetch_networkinfo() -> None:
    networkinfo = exec_rpc_call("getnetworkinfo")
    if networkinfo is not None:
        UTXO_NODE_PEERS.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(networkinfo["connections"])
        if "connections_in" in networkinfo:
            UTXO_NODE_CONN_IN.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(networkinfo["connections_in"])
        if "connections_out" in networkinfo:
            UTXO_NODE_CONN_OUT.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(networkinfo["connections_out"])

        UTXO_NODE_SERVER_VERSION.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(networkinfo["version"])
        UTXO_NODE_PROTOCOL_VERSION.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(networkinfo["protocolversion"])

        if networkinfo["warnings"]:
            UTXO_NODE_WARNINGS.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).inc()

def fetch_chaintips() -> None:
    chaintips = exec_rpc_call("getchaintips")
    if chaintips is not None:
        UTXO_NODE_NUM_CHAINTIPS.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(len(chaintips))

def fetch_mempoolinfo() -> None:
    mempool = exec_rpc_call("getmempoolinfo")
    if mempool is not None:
        UTXO_NODE_MEMPOOL_BYTES.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(mempool["bytes"])
        UTXO_NODE_MEMPOOL_SIZE.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(mempool["size"])
        UTXO_NODE_MEMPOOL_USAGE.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(mempool["usage"])
        if "unbroadcastcount" in mempool:
            UTXO_NODE_MEMPOOL_UNBROADCAST.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(mempool["unbroadcastcount"])

def fetch_nettotals() -> None:
    nettotals = exec_rpc_call("getnettotals")
    if nettotals is not None:
        UTXO_NODE_TOTAL_BYTES_RECV.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(nettotals["totalbytesrecv"])
        UTXO_NODE_TOTAL_BYTES_SENT.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(nettotals["totalbytessent"])

def fetch_rpcinfo() -> None:
    rpcinfo = exec_rpc_call("getrpcinfo")
    if rpcinfo is not None:
        # Subtract one because we don't want to count the "getrpcinfo" call itself
        UTXO_NODE_RPC_ACTIVE.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(len(rpcinfo["active_commands"]) - 1)

def fetch_txstats() -> None:
    txstats = exec_rpc_call("getchaintxstats")
    if txstats is not None:
        UTXO_NODE_TXCOUNT.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).set(txstats["txcount"])

def fetch_banned() -> None:
    banned = exec_rpc_call("listbanned")
    if banned is not None:
        for ban in banned:
            UTXO_NODE_BAN_CREATED.labels(
                address=ban["address"],
                reason=ban.get("ban_reason", "manually added"),
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME
            ).set(ban["ban_created"])
            UTXO_NODE_BANNED_UNTIL.labels(
                address=ban["address"],
                reason=ban.get("ban_reason", "manually added"),
                blockchain=UTXO_NODE_BLOCKCHAIN_NAME
            ).set(ban["banned_until"])


def fetch_smart_fees() -> None:
    for smartfee in SMART_FEES:
        do_smartfee(smartfee)

def fetch_hashp_blocks() -> None:
    for hashps_block in HASHPS_BLOCKS:
        do_hashps_gauge(hashps_block)

def build_functions_dict() -> Dict[str, Callable[[], None]]:
    functions_dict = {}
    if FETCH_UPTIME:
        functions_dict['uptime'] = fetch_uptime
    if FETCH_MEMINFO:
        functions_dict['meminfo'] = fetch_meminfo
    if FETCH_BLOCKCHAININFO:
        functions_dict['blockchaininfo'] = fetch_blockchaininfo
    if FETCH_BLOCKSTATS:
        functions_dict['blockstats'] = fetch_blockstats
    if FETCH_NETWORKINFO:
        functions_dict['networkinfo'] = fetch_networkinfo
    if FETCH_CHAINTIPS:
        functions_dict['chaintips'] = fetch_chaintips
    if FETCH_MEMPOOLINFO:
        functions_dict['mempoolinfo'] = fetch_mempoolinfo
    if FETCH_NETTOTALS:
        functions_dict['nettotals'] = fetch_nettotals
    if FETCH_RPCINFO:
        functions_dict['rpcinfo'] = fetch_rpcinfo
    if FETCH_TXSTATS:
        functions_dict['txstats'] = fetch_txstats
    if FETCH_BANNED:
        functions_dict['banned'] = fetch_banned
    if FETCH_SMART_FEES:
        functions_dict['smart_fees'] = fetch_smart_fees
    if FETCH_HASHP_BLOCKS:
        functions_dict['hashp_blocks'] = fetch_hashp_blocks

    return functions_dict

def fetch(fetch_function):
    # Allow riprova.MaxRetriesExceeded and unknown exceptions to crash the process.
    try:
        logger.info("Fetching metric...")
        fetch_function()
    except riprova.exceptions.RetryError as e:
        logger.error("Fetch failed during retry. Cause: " + str(e))
        exception_count(e)
    except JSONRPCError as e:
        logger.debug("RPC error refresh", exc_info=True)
        exception_count(e)
    except json.decoder.JSONDecodeError as e:
        logger.error("RPC call did not return JSON. Bad credentials? " + str(e))
        sys.exit(1)

def main():
    logging.basicConfig(format=LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%SZ")
    logging.Formatter.converter = time.gmtime
    logger.setLevel(LOG_LEVEL)

    # Handle SIGTERM gracefully.
    signal.signal(signal.SIGTERM, sigterm_handler)

    app = make_wsgi_app()

    last_refresh = datetime.fromtimestamp(0)

    functions_dict = build_functions_dict()
    logger.info("The following data will be fetched: %s", ', '.join([k for k in functions_dict.keys()]))

    def refresh_app(*args, **kwargs):
        nonlocal last_refresh
        process_start = datetime.now()

        # Only refresh every RATE_LIMIT_SECONDS seconds.
        if (process_start - last_refresh).total_seconds() < RATE_LIMIT_SECONDS:
            return app(*args, **kwargs)

        for func_name, func in functions_dict.items():
            fetch(func)

        duration = datetime.now() - process_start
        PROCESS_TIME.labels(blockchain=UTXO_NODE_BLOCKCHAIN_NAME).inc(duration.total_seconds())
        logger.info("Fetch took %s seconds", duration)
        last_refresh = process_start

        return app(*args, **kwargs)

    httpd = make_server(METRICS_ADDR, METRICS_PORT, refresh_app)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
