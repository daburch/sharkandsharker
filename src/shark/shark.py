import logging
from dataclasses import dataclass
from shark.packet_monitor import PacketMonitor, PacketMonitorConfig

logger = logging.getLogger(__name__)


@dataclass
class SharkConfig:
    interface: str  # The local network interface to listen on
    ips: str  # The IP addresses to listen for packets from


class Shark:
    def __init__(self, config: SharkConfig):
        self.config = config

        # Create a packet monitor to listen for packets to and from the specified IP addresses
        self.packet_monitor = PacketMonitor(
            PacketMonitorConfig(
                interface=self.config.interface,
                bpf_filter=" or ".join(
                    [f"src host {ip} or dst host {ip}" for ip in config.ips]
                ),
            )
        )

    def begin_monitoring(self):
        """
        Monitor network traffic for marketplace data packets.
        """
        self.packet_monitor.begin_monitoring()
