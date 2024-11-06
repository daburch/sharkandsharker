import argparse
import logging
import threading
import time
import keyboard

from shark.shark import Shark, SharkConfig
from config import MONITORED_IPS, LOCAL_DEFAULT_INTERFACE

logger = logging.getLogger(__name__)


def inspect(shark: Shark):
    try:
        t = threading.Thread(target=shark.packet_monitor.begin_monitoring)

        t.start()

        # infinite loop to print out the results of the watcher thread marketplace responses
        l = len(shark.packet_monitor.responses)
        while True:
            if shark.is_stopped():
                break

            # print a simplified version of the most recent response if there is a new one
            if l != len(shark.packet_monitor.responses):
                for item in shark.packet_monitor.responses[-1].items:
                    logger.info(f"{item.name}: {item.price}")

                l = len(shark.packet_monitor.responses)

            time.sleep(1)
    finally:
        t.join()


def listen_for_keypress(shark: Shark):
    keyboard.wait("`")
    logger.info("Keypress detected. Stopping all threads.")
    shark.end_monitoring()


def main():
    """
    Main driver function for Shark and Sharker.

    Based on the mode of operation, routes the program to the appropriate logic.

    Modes:
        - inspect: Creates a packet watcher but doesn't automatically scan the marketplace; allows manual scans.
        - gather: Creates a packet watcher and automatically scans the marketplace to collect large training datasets.
        - train: Trains the model using the gathered data.
        - predict: Uses the trained model to predict prices.

    Arguments:
        --mode: Mode of operation (choices: "inspect", "gather", "train", "predict"). Default is "predict".
    """
    logging.basicConfig(format="%(levelname)-8s :: %(message)s", level=logging.INFO)

    parser = argparse.ArgumentParser(description="Shark and Sharker")
    parser.add_argument(
        "--mode",
        type=str,
        default="predict",
        required=False,
        help="Mode of operation",
        choices=["inspect", "gather", "train", "predict"],
    )
    args = parser.parse_args()

    if args.mode == "inspect":
        # Inspect Mode creates a packet watcher but doesn't automatically scan the marketplace; allowing manual scans.
        shark = Shark(SharkConfig(interface=LOCAL_DEFAULT_INTERFACE, ips=MONITORED_IPS))
        packet_monitor_thread = threading.Thread(target=inspect, args=(shark,))
        keypress_listener_thread = threading.Thread(
            target=listen_for_keypress, args=(shark,)
        )

        packet_monitor_thread.start()
        keypress_listener_thread.start()

        packet_monitor_thread.join()
        keypress_listener_thread.join()

    elif args.mode == "gather":
        # Gather Mode creates a packet watcher and automatically scans the marketplace to collect large training datasets.
        logger.info("TODO: Implement gather mode")
    elif args.mode == "train":
        # Train Mode trains the model using the gathered data.
        logger.info("TODO: Implement train mode")
    elif args.mode == "predict":
        # Predict Mode uses the trained model to predict prices.
        logger.info("TODO: Implement predict mode")
    else:
        logger.error("Invalid mode")


if __name__ == "__main__":
    main()
