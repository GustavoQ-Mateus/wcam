from collections.abc import Awaitable, Callable

from aiortc import RTCPeerConnection

LOOPBACK = "127.0.0.1"
AIORTC_ICE_CONNECTION_ATTRIBUTE = "_connection"
AIOICE_CANDIDATES_METHOD = "get_component_candidates"

type CandidateGatherer = Callable[..., Awaitable[list[object]]]


def gather_only_on_loopback(connection: RTCPeerConnection) -> None:
    # aioice gathers on every interface except 127.0.0.1 and has no option to choose; the preview lives on loopback.
    for transceiver in connection.getTransceivers():
        gatherer = transceiver.sender.transport.transport.iceGatherer
        ice = getattr(gatherer, AIORTC_ICE_CONNECTION_ATTRIBUTE)
        gather: CandidateGatherer = getattr(ice, AIOICE_CANDIDATES_METHOD)
        setattr(ice, AIOICE_CANDIDATES_METHOD, loopback_candidates(gather))


def loopback_candidates(gather: CandidateGatherer) -> CandidateGatherer:
    async def candidates(component: int, addresses: list[str], **options: object) -> list[object]:
        return await gather(component=component, addresses=[LOOPBACK], **options)

    return candidates
