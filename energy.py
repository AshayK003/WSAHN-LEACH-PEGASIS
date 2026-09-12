"""First-order radio energy model (Heinzelman et al.)"""

# Energy parameters (standard values from LEACH paper)
E_ELEC = 50e-9      # J/bit - electronics energy
E_FS = 10e-12       # J/bit/m^2 - free space amp
E_MP = 0.0013e-12   # J/bit/m^4 - multipath amp
D0 = (E_FS / E_MP) ** 0.5  # crossover distance ~87m

PACKET_SIZE = 4000  # bits

# Traffic-model harness for aggregation robustness checks (see
# cch_aggregation.py). Scales the effective payload of every tx/rx/da
# charge. 1.0 = the published first-order radio model, bit-identical.
PAYLOAD_SCALE = 1.0


def _bits():
    return PACKET_SIZE * PAYLOAD_SCALE

# Node-to-node transmission range (m). A link longer than COMM_RANGE cannot
# deliver its packet (range-induced packet loss). Set to None for an unlimited
# range (distance affects only the energy cost, as in vanilla LEACH/PEGASIS).
# This is a configurable simulation parameter required by the mini-project
# guidelines (communication range). The base station / sink hop is exempt:
# the sink is assumed to have its own longer range.
COMM_RANGE = None


def in_range(distance: float) -> bool:
    """True if a transmission over `distance` can be received."""
    return COMM_RANGE is None or distance <= COMM_RANGE


def tx_energy(distance: float) -> float:
    """Energy to transmit PACKET_SIZE bits over distance."""
    if distance < D0:
        return _bits() * (E_ELEC + E_FS * distance ** 2)
    return _bits() * (E_ELEC + E_MP * distance ** 4)


def rx_energy() -> float:
    """Energy to receive PACKET_SIZE bits."""
    return _bits() * E_ELEC


def da_energy() -> float:
    """Data aggregation energy per packet (typically 5 nJ/bit)."""
    return _bits() * 5e-9