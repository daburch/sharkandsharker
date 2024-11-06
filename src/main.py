import argparse
import logging
import threading
import time

from shark.shark import Shark, SharkConfig
from shark.marketplace_response import Item

from sharker.sharker import Sharker, SharkerConfig

from config import MONITORED_IPS, LOCAL_DEFAULT_INTERFACE, DATA_DIR

logger = logging.getLogger(__name__)


def inspect(shark: Shark):
    l = len(shark.packet_monitor.responses)
    while not shark.is_stopped():
        # print a simplified version of the most recent response if there is a new one
        if l != len(shark.packet_monitor.responses):
            for item in shark.packet_monitor.responses[-1].items:
                logger.info(f"{item.name}: {item.price}")

            l = len(shark.packet_monitor.responses)

        time.sleep(1)


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
        choices=["inspect", "scan", "train", "predict"],
    )
    args = parser.parse_args()

    if args.mode == "inspect":
        # Inspect Mode creates a packet watcher but doesn't automatically scan the marketplace; allowing manual scans.
        shark = Shark(
            SharkConfig(
                interface=LOCAL_DEFAULT_INTERFACE,
                ips=MONITORED_IPS,
                data_dir=f"{DATA_DIR}\export",
            )
        )
        packet_monitor_thread = threading.Thread(
            target=shark.packet_monitor.begin_monitoring
        )
        keypress_listener_thread = threading.Thread(target=shark.listen_for_keypress)
        packet_logger_thread = threading.Thread(target=inspect, args=(shark,))

        packet_monitor_thread.start()
        keypress_listener_thread.start()
        packet_logger_thread.start()

        packet_monitor_thread.join()
        keypress_listener_thread.join()
        packet_logger_thread.join()

        logger.info("Shark and Sharker has stopped.")
        logger.info(f"Collected {len(shark.packet_monitor.responses)} responses.")

        shark.export_data()

    elif args.mode == "scan":
        # scan Mode creates a packet watcher and automatically scans the marketplace to collect large training datasets.
        logger.info("TODO: Implement scan mode")
    elif args.mode == "train":
        # Train Mode trains the model using the gathered data.
        sharker = Sharker(
            SharkerConfig(
                model_path=f"{DATA_DIR}",
                model_name=f"model.pkl",
                raw_data_path=f"{DATA_DIR}\export",
                prepared_data_path=f"{DATA_DIR}\prepared",
            )
        )

        sharker.train()
    elif args.mode == "predict":
        # Predict Mode uses the trained model to predict prices.
        sharker = Sharker(
            SharkerConfig(
                model_path=f"{DATA_DIR}",
                model_name=f"model.pkl",
                raw_data_path=f"{DATA_DIR}\export",
                prepared_data_path=f"{DATA_DIR}\prepared",
            )
        )

        sample_item_raw = {
            "name": "AdventurerBoots",
            "rarity": "Unique",
            "stack_count": 1,
            "properties": {
                "ArmorRating": 25,
                "MoveSpeed": 6,
                "Dexterity": 7,
                "MemoryCapacityBonus": 50,
                "MagicalDamageReduction": 6,
                "ProjectileReductionMod": 10,
                "BuffDurationBonus": 48,
                "MemoryCapacityAdd": 2,
            },
            "loot_state": "Looted",
            "found_by_name": "Love2Fuk",
            "found_by_tag": "Barbarian#11123811",
            "sold_by_name": "Love2Fuk",
            "sold_by_tag": "Barbarian#11123811",
            "sold_by_leaderboard_rank": "Apprentice_I",
            "price": 333,
            "expiry_ts": "2024-11-12T17:42:12.508182",
        }
        prediction = sharker.predict(Item.from_dict(sample_item_raw))
        logger.info(f"Predicted price: {prediction}")
    else:
        logger.error("Invalid mode")


if __name__ == "__main__":
    main()
