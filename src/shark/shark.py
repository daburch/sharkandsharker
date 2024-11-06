import logging
import pywinauto
import asyncio
import keyboard
import json
import os
from datetime import datetime

from dataclasses import dataclass
from shark.packet_monitor import PacketMonitor, PacketMonitorConfig

logger = logging.getLogger(__name__)


@dataclass
class SharkConfig:
    interface: str  # The local network interface to listen on
    ips: str  # The IP addresses to listen for packets from
    data_dir: str  # The directory to save data to


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

    def scan(self):
        """
        Scan the marketplace for data packets.
        """
        pass

    def listen_for_keypress(self):
        """
        Listen for keypresses to control the program.
        """
        keyboard.wait("`")
        logger.info("Keypress detected. Stopping all threads.")
        self.end_monitoring()

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

    def export_data(self):
        """
        Export the collected data to a file.
        """
        if not os.path.exists(self.config.data_dir):
            os.makedirs(self.config.data_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.config.data_dir, f"responses_{timestamp}.json")
        items = [
            item.dict()
            for response in self.packet_monitor.responses
            for item in response.items
        ]
        with open(filename, "w") as f:
            json.dump(items, f, indent=4)

        logger.info(f"Saved {len(items)} responses to {filename}")
