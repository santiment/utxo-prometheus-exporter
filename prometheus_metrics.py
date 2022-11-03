from decimal import Decimal
from prometheus_client import Gauge, Counter

METRIC_PREFIX = "utxo_node"

UTXO_NODE_BLOCKS = Gauge(f"{METRIC_PREFIX}_blocks", "Block height")
UTXO_NODE_DIFFICULTY = Gauge(f"{METRIC_PREFIX}_difficulty", "Difficulty")
UTXO_NODE_PEERS = Gauge(f"{METRIC_PREFIX}_peers", "Number of peers")
UTXO_NODE_CONN_IN = Gauge(f"{METRIC_PREFIX}_conn_in", "Number of connections in")
UTXO_NODE_CONN_OUT = Gauge(f"{METRIC_PREFIX}_conn_out", "Number of connections out")

UTXO_NODE_HASHPS_GAUGES = {}  # type: Dict[int, Gauge]
UTXO_NODE_ESTIMATED_SMART_FEE_GAUGES = {}  # type: Dict[int, Gauge]

UTXO_NODE_WARNINGS = Counter(
    f"{METRIC_PREFIX}_warnings",
    "Number of network or blockchain warnings detected"
)
UTXO_NODE_UPTIME = Gauge(
    f"{METRIC_PREFIX}_uptime",
    "Number of seconds the node has been running"
)

UTXO_NODE_MEMINFO_USED = Gauge(f"{METRIC_PREFIX}_meminfo_used", "Number of bytes used")
UTXO_NODE_MEMINFO_FREE = Gauge(f"{METRIC_PREFIX}_meminfo_free", "Number of bytes available")
UTXO_NODE_MEMINFO_TOTAL = Gauge(f"{METRIC_PREFIX}_meminfo_total", "Number of bytes managed")
UTXO_NODE_MEMINFO_LOCKED = Gauge(f"{METRIC_PREFIX}_meminfo_locked", "Number of bytes locked")
UTXO_NODE_MEMINFO_CHUNKS_USED = Gauge(f"{METRIC_PREFIX}_meminfo_chunks_used", "Number of allocated chunks")
UTXO_NODE_MEMINFO_CHUNKS_FREE = Gauge(f"{METRIC_PREFIX}_meminfo_chunks_free", "Number of unused chunks")

UTXO_NODE_MEMPOOL_BYTES = Gauge(f"{METRIC_PREFIX}_mempool_bytes", "Size of mempool in bytes")
UTXO_NODE_MEMPOOL_SIZE = Gauge(
    f"{METRIC_PREFIX}_mempool_size", "Number of unconfirmed transactions in mempool"
)
UTXO_NODE_MEMPOOL_USAGE = Gauge(f"{METRIC_PREFIX}_mempool_usage", "Total memory usage for the mempool")
UTXO_NODE_MEMPOOL_UNBROADCAST = Gauge(
    f"{METRIC_PREFIX}_mempool_unbroadcast", "Number of transactions waiting for acknowledgment"
)

UTXO_NODE_LATEST_BLOCK_HEIGHT = Gauge(
    f"{METRIC_PREFIX}_latest_block_height", "Height or index of latest block"
)
UTXO_NODE_LATEST_BLOCK_WEIGHT = Gauge(
    f"{METRIC_PREFIX}_latest_block_weight", "Weight of latest block according to BIP 141"
)
UTXO_NODE_LATEST_BLOCK_SIZE = Gauge(f"{METRIC_PREFIX}_latest_block_size", "Size of latest block in bytes")
UTXO_NODE_LATEST_BLOCK_TXS = Gauge(
    f"{METRIC_PREFIX}_latest_block_txs", "Number of transactions in latest block"
)

UTXO_NODE_TXCOUNT = Gauge(f"{METRIC_PREFIX}_txcount", "Number of TX since the genesis block")

UTXO_NODE_NUM_CHAINTIPS = Gauge(f"{METRIC_PREFIX}_num_chaintips", "Number of known blockchain branches")

UTXO_NODE_TOTAL_BYTES_RECV = Gauge(f"{METRIC_PREFIX}_total_bytes_recv", "Total bytes received")
UTXO_NODE_TOTAL_BYTES_SENT = Gauge(f"{METRIC_PREFIX}_total_bytes_sent", "Total bytes sent")

UTXO_NODE_LATEST_BLOCK_INPUTS = Gauge(
    f"{METRIC_PREFIX}_latest_block_inputs", "Number of inputs in transactions of latest block"
)
UTXO_NODE_LATEST_BLOCK_OUTPUTS = Gauge(
    f"{METRIC_PREFIX}_latest_block_outputs", "Number of outputs in transactions of latest block"
)
UTXO_NODE_LATEST_BLOCK_VALUE = Gauge(
    f"{METRIC_PREFIX}_latest_block_value", "Bitcoin value of all transactions in the latest block"
)
UTXO_NODE_LATEST_BLOCK_FEE = Gauge(
    f"{METRIC_PREFIX}_latest_block_fee", "Total fee to process the latest block"
)

UTXO_NODE_BAN_CREATED = Gauge(
    f"{METRIC_PREFIX}_ban_created", "Time the ban was created", labelnames=["address", "reason"]
)
UTXO_NODE_BANNED_UNTIL = Gauge(
    f"{METRIC_PREFIX}_banned_until", "Time the ban expires", labelnames=["address", "reason"]
)

UTXO_NODE_SERVER_VERSION = Gauge(f"{METRIC_PREFIX}_server_version", "The server version")
UTXO_NODE_PROTOCOL_VERSION = Gauge(f"{METRIC_PREFIX}_protocol_version", "The protocol version of the server")

UTXO_NODE_SIZE_ON_DISK = Gauge(f"{METRIC_PREFIX}_size_on_disk", "Estimated size of the block and undo files")

UTXO_NODE_VERIFICATION_PROGRESS = Gauge(
    f"{METRIC_PREFIX}_verification_progress", "Estimate of verification progress [0..1]"
)

UTXO_NODE_RPC_ACTIVE = Gauge(f"{METRIC_PREFIX}_rpc_active", "Number of RPC calls being processed")

EXPORTER_ERRORS = Counter(
    f"{METRIC_PREFIX}_exporter_errors", "Number of errors encountered by the exporter", labelnames=["type"]
)
PROCESS_TIME = Counter(
    f"{METRIC_PREFIX}_exporter_process_time", "Time spent processing metrics from node"
)

SATS_PER_COIN = Decimal(1e8)

def hashps_gauge_suffix(nblocks):
    if nblocks < 0:
        return "_neg%d" % -nblocks
    if nblocks == 120:
        return ""
    return "_%d" % nblocks


def hashps_gauge(num_blocks: int) -> Gauge:
    gauge = UTXO_NODE_HASHPS_GAUGES.get(num_blocks)
    if gauge is None:
        desc_end = "for the last %d blocks" % num_blocks
        if num_blocks == -1:
            desc_end = "since the last difficulty change"
        gauge = Gauge(
            f"{METRIC_PREFIX}_hashps%s" % hashps_gauge_suffix(num_blocks),
            "Estimated network hash rate per second %s" % desc_end,
        )
        UTXO_NODE_HASHPS_GAUGES[num_blocks] = gauge
    return gauge

def smartfee_gauge(num_blocks: int) -> Gauge:
    gauge = UTXO_NODE_ESTIMATED_SMART_FEE_GAUGES.get(num_blocks)
    if gauge is None:
        gauge = Gauge(
            f"{METRIC_PREFIX}_est_smart_fee_%d" % num_blocks,
            "Estimated smart fee per kilobyte for confirmation in %d blocks" % num_blocks,
        )
        UTXO_NODE_ESTIMATED_SMART_FEE_GAUGES[num_blocks] = gauge
    return gauge
