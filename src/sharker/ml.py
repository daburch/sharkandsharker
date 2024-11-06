import joblib
import logging
import os

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

logger = logging.getLogger(__name__)


def prepare_data(raw_data):
    data = []
    for item in raw_data:
        item_data = {
            "name": item.name,
            "rarity": item.rarity,
            "count": item.stack_count,
            "price": item.price,
        }
        item_data.update(item.properties)
        data.append(item_data)

    df = pd.DataFrame(data)

    # Replace NaNs with zeros
    df.fillna(0, inplace=True)

    return df


def train_model(data, model_dir):
    x = data.drop(columns=["price"])
    y = data["price"]

    # One-hot encode categorical variables
    categorical_features = ["name", "rarity"]
    categorical_transformer = OneHotEncoder()

    preprocessor = ColumnTransformer(
        transformers=[("cat", categorical_transformer, categorical_features)],
        remainder="passthrough",
    )

    model = Pipeline(
        steps=[("preprocessor", preprocessor), ("regressor", LinearRegression())]
    )

    model.fit(x, y)

    # Save the column names
    column_names = x.columns.tolist()
    joblib.dump(column_names, f"{model_dir}\column_names.pkl")

    return model


def predict_price(model_dir, model, items):
    df = prepare_data(items)

    # Log the DataFrame to debug
    logging.debug(f"DataFrame for prediction:\n{df}")

    # Load the column names from the training data
    column_names = joblib.load(os.path.join(model_dir, "column_names.pkl"))

    # Ensure the DataFrame has the same columns as the training data
    for column in column_names:
        if column not in df.columns:
            df[column] = 0

    # Check if the DataFrame is empty
    if df.empty:
        raise ValueError(
            "The DataFrame for prediction is empty. Ensure the item data is correctly added."
        )

    predictions = model.predict(df)
    return predictions


def save_model(model, filename):
    joblib.dump(model, filename)


def load_model(filename):
    return joblib.load(filename)
