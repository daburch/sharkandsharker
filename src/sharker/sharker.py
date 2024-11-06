import logging
import os
import json
import pandas as pd

from dataclasses import dataclass

from sharker.ml import load_model, save_model, prepare_data, train_model, predict_price
from shark.marketplace_response import Item

logger = logging.getLogger(__name__)


@dataclass
class SharkerConfig:
    model_path: str  # The model path
    model_name: str  # The model name
    raw_data_path: str  # The location of raw data exports from Shark
    prepared_data_path: str  # The location to save prepared data for training


class Sharker:
    def __init__(self, config: SharkerConfig):
        self.config = config
        self.model = self.import_model()

    def import_model(self):
        """
        Import the model from the specified path.
        """
        if not os.path.exists(
            os.path.join(self.config.model_path, self.config.model_name)
        ):
            return None

        return load_model(os.path.join(self.config.model_path, self.config.model_name))

    def export_model(self):
        """
        Export the model to the specified path.
        """
        save_model(
            self.model, os.path.join(self.config.model_path, self.config.model_name)
        )

    def train(self):
        """
        Train the model using the specified data.
        """
        raw_data = self.__load_raw_data_files()
        prepared_data = prepare_data(raw_data)
        self.model = train_model(prepared_data, self.config.model_path)
        self.export_model()
        logger.info("Model trained and saved.")

    def __load_raw_data_files(self):
        """
        Load all raw data files from the specified directory.
        """
        all_items = []
        for filename in os.listdir(self.config.raw_data_path):
            if filename.endswith(".json"):
                filepath = os.path.join(self.config.raw_data_path, filename)
                with open(filepath, "r") as f:
                    items = json.load(f)
                    all_items.extend(Item.from_dict(item) for item in items)
        logger.info(
            f"Loaded {len(all_items)} items from {len(os.listdir(self.config.raw_data_path))} files."
        )
        return all_items

    def predict(self, item):
        """
        Predict the price of the specified data.
        """
        if self.model is None:
            logger.error("Model has not been trained yet.")
            return None

        predictions = predict_price(self.config.model_path, self.model, [item])

        return predictions[0]
