import logging
import pyshark

from pyshark.packet.packet import Packet

from dataclasses import dataclass

from shark.marketplace_response import (
    MarketplaceResponse,
    begins_marketplace_response,
    ends_marketplace_response,
)
from config import MONITORED_IPS
from constants import KEEP_ALIVE_RESPONSE

logger = logging.getLogger(__name__)


@dataclass
class PacketMonitorConfig:
    interface: str  # The local network interface to listen on
    bpf_filter: str  # The BPF filter to apply to the network interface


class PacketMonitor:
    def __init__(self, config: PacketMonitorConfig):
        self.interface = config.interface
        self.bpf_filter = config.bpf_filter
        self.ack_map = {}

    def begin_monitoring(self):
        """
        Begin monitoring network traffic on the specified interface.
        """
        logger.info(
            f"Monitoring network traffic on {self.interface} with BPF filter: {self.bpf_filter}"
        )

        capture = pyshark.LiveCapture(
            interface=self.interface,
            bpf_filter=self.bpf_filter,
        )

        for packet in capture.sniff_continuously():
            self.process_packet(packet)

    def process_packet(self, packet: Packet):
        """
        Process a packet captured from the network interface.
        """
        if packet.ip.dst in MONITORED_IPS:
            logger.debug("sent packet to Ironmace")

        if packet.ip.src in MONITORED_IPS:
            logger.debug("received packet from Ironmace")
            self.process_response_packet(packet)

    def process_response_packet(self, packet: Packet):
        """
        Process a response packet captured from the network interface.
        """
        payload = get_payload(packet)
        if payload is None:
            return

        if payload.hex() == KEEP_ALIVE_RESPONSE:
            logger.debug("keep-alive ping received from ironmace")
            return

        ack = int(packet.tcp.ack)
        seq = int(packet.tcp.seq)
        nxt = int(packet.tcp.nxtseq)

        # TODO: is it possible for the first part of a response to come after subsequent parts?
        # If this is possible, the segments when arrived before the first piece will be lost
        # causing the payload the be incomplete and breaking parsing logic.

        # responses can come in multiple segments, so we need to keep track of them
        # multiple segments can be identified by the same ack number
        if begins_marketplace_response(payload):
            logger.debug("received start of marketplace response")
            if ack not in self.ack_map:
                # the ack map consists of 2 pieces.
                # segments: the payload
                # sequence: the next expected sequence number
                self.ack_map[ack] = {"segments": {}, "sequence": {}}

        # if the ack is in the ack_map, this is a continuation of a previous response
        if ack in self.ack_map:
            logger.debug(f"Received segment {seq} for ack {ack}, nxt: {nxt}")
            self.ack_map[ack]["segments"][seq] = payload

            # set the next expected sequence number for the ack
            if not ends_marketplace_response(payload):
                logger.debug(f"Segment {seq} is not complete. NXT: {nxt}")
                self.ack_map[ack]["sequence"][seq] = nxt

            # check each sequence number for the next expected segment
            # if that expected segment hasn't yet arrived, wait for it before processing
            for seq, nxt in self.ack_map[ack]["sequence"].items():
                if nxt and nxt not in self.ack_map[ack]["segments"]:
                    logger.debug(f"Waiting for segment {nxt} for ack {ack}")
                    return None

            # if all segments have arrived, process the response
            logger.debug(f"Received all segments for ack {ack}")

            reconstructed_payload = self.__reconstruct_payload(ack)
            try:
                response = MarketplaceResponse(reconstructed_payload)
                logger.info(f"Marketplace response: {response.dump()}")
            except ValueError as e:
                logger.error(f"Failed to parse marketplace response: {e}")

    def __reconstruct_payload(self, ack: int) -> bytearray:
        """
        Reconstruct the payload from the segments.
        """
        sorted_segments = sorted(self.ack_map[ack]["segments"].items())
        reconstructed_payload = bytearray()
        for _, segment in sorted_segments:
            reconstructed_payload.extend(segment)

        return reconstructed_payload


def get_payload(packet: Packet) -> bytearray | None:
    """
    Extract the payload from a packet and replace colons with empty strings to give a hex byte array.
    """
    try:
        b = bytearray()
        for bc in packet.tcp.payload.split(":"):
            b.append(
                int(bc, 16)
            )  # Convert each hex string to a byte and append to the bytearray
        return b
    except AttributeError:
        return None
