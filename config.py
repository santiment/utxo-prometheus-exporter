import os
from distutils.util import strtobool

# Set up logging to look similar to bitcoin logs (UTC).
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

UTXO_NODE_BLOCKCHAIN_NAME = os.environ.get("UTXO_NODE_BLOCKCHAIN_NAME", "bitcoin")

UTXO_NODE_RPC_SCHEME = os.environ.get("UTXO_NODE_RPC_SCHEME", "http")
UTXO_NODE_RPC_HOST = os.environ.get("UTXO_NODE_RPC_HOST", "localhost")
UTXO_NODE_RPC_PORT = os.environ.get("UTXO_NODE_RPC_PORT", "8332")
UTXO_NODE_RPC_USER = os.environ.get("UTXO_NODE_RPC_USER")
UTXO_NODE_RPC_PASSWORD = os.environ.get("UTXO_NODE_RPC_PASSWORD")
UTXO_NODE_CONF_PATH = os.environ.get("UTXO_NODE_CONF_PATH")
HASHPS_BLOCKS = [int(b) for b in os.environ.get("HASHPS_BLOCKS", "-1,1,120").split(",") if b != ""]
SMART_FEES = [int(f) for f in os.environ.get("SMARTFEE_BLOCKS", "2,3,5,20").split(",") if f != ""]
METRICS_ADDR = os.environ.get("METRICS_ADDR", "")  # empty = any address
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9332"))
RETRIES = int(os.environ.get("RETRIES", 5))
TIMEOUT = int(os.environ.get("TIMEOUT", 30))
RATE_LIMIT_SECONDS = int(os.environ.get("RATE_LIMIT", 5))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

FETCH_UPTIME = strtobool(os.environ.get("FETCH_UPTIME", 'True'))
FETCH_MEMINFO = strtobool(os.environ.get("FETCH_MEMINFO", 'True'))
FETCH_BLOCKCHAININFO = strtobool(os.environ.get("FETCH_BLOCKCHAININFO", 'True'))
FETCH_NETWORKINFO = strtobool(os.environ.get("FETCH_NETWORKINFO", 'True'))
FETCH_CHAINTIPS = strtobool(os.environ.get("FETCH_CHAINTIPS", 'True'))
FETCH_MEMPOOLINFO = strtobool(os.environ.get("FETCH_MEMPOOLINFO", 'True'))
FETCH_NETTOTALS = strtobool(os.environ.get("FETCH_NETTOTALS", 'True'))
FETCH_RPCINFO = strtobool(os.environ.get("FETCH_RPCINFO", 'True'))
FETCH_TXSTATS = strtobool(os.environ.get("FETCH_TXSTATS", 'True'))
FETCH_BANNED = strtobool(os.environ.get("FETCH_BANNED", 'True'))
FETCH_SMART_FEES = strtobool(os.environ.get("FETCH_SMART_FEES", 'True'))
FETCH_HASHP_BLOCKS = strtobool(os.environ.get("FETCH_HASHP_BLOCKS", 'True'))