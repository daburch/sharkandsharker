import logging
import pywinauto
import asyncio

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

        self.window = pywinauto.Application().connect(path="Dark and Darker")[
            "Dark and Darker"
        ]

    def begin_monitoring(self):
        """
        Monitor network traffic for marketplace data packets.
        """
        asyncio.run(self.packet_monitor.begin_monitoring())

    def end_monitoring(self):
        """
        Stop monitoring network traffic.
        """
        self.packet_monitor.end_monitoring()

    def is_stopped(self):
        """
        Check if the packet monitor has been stopped.
        """
        return self.packet_monitor.is_stopped()
