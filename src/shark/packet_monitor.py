import logging
import pyshark

from pyshark.packet.packet import Packet

from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PacketMonitorConfig:
    interface: str  # The local network interface to listen on
    bpf_filter: str  # The BPF filter to apply to the network interface


class PacketMonitor:
    def __init__(self, config: PacketMonitorConfig):
        self.interface = config.interface
        self.bpf_filter = config.bpf_filter

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
        logger.info("received packet")
        logger.info(f"Source IP: {packet.ip.src}")
        logger.info(f"Destination IP: {packet.ip.dst}")

        payload = get_payload(packet)
        logger.info(f"payload: {payload}")


def get_payload(packet: Packet) -> bytearray | None:
    try:
        b = bytearray()
        b.extend(map(ord, packet.tcp.payload.replace(":", "")))
        return b
    except AttributeError:
        return None
