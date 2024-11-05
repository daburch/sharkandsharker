import logging
import json

from utils import vlq_decode_little_endian, vlq_decode_big_endian

from constants import (
    MARKETPLACE_RESPONSE_HEADER,
    H_ITEM_ID,
    H_ITEM_PROPERTY,
    H_LEADERBOARD_RANK,
)
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Item:
    def __init__(self, payload):
        self.payload = payload
        self.properties = {}
        self.price = 0
        self.__parse()

    def __parse(self):
        if self.payload is None:
            return

        id_start = self.__parse_header()
        name_end = self.__parse_item_id(id_start)
        stack_count_end = self.__parse_stack_count(name_end)
        item_properties_end = self.__parse_item_properties(stack_count_end)
        loot_state_end = self.__parse_loot_state(item_properties_end)
        found_by_end = self.__parse_found_by(loot_state_end)
        price_end = self.__parse_price(found_by_end)
        ts_end = self.__parse_ts(price_end)
        self.__parse_sold_by(ts_end)

    def __parse_header(self):
        id_start = self.payload.find(H_ITEM_ID)
        if id_start == -1:
            raise ValueError("ID not found in item payload")

        # These are unknown bytes that appear before the item ID.
        self.header_bytes = self.payload[0:id_start]
        return id_start

    def __parse_item_id(self, start_index):
        id_end = start_index + len(H_ITEM_ID)
        name_end = self.payload.find(b"\x18", id_end)
        if name_end == -1:
            raise ValueError("name not found in item payload")

        id = self.payload[id_end:name_end]

        # ID is a combination of name and rarity, separated by _
        spl = id.split(b"_")

        if len(spl) == 2:
            self.name = spl[0].decode("utf-8")
            self.rarity = rarity_str(spl[1].decode("utf-8"))
        else:
            # no rarity present
            self.name = spl[0].decode("utf-8")
            self.rarity = rarity_str(None)

        return name_end

    def __parse_stack_count(self, start_index):
        if self.payload[start_index : start_index + 1] != b"\x18":
            raise ValueError("stack count not found in item payload")

        # stack count is a single byte after the 0x18 byte
        self.stack_count = int(
            self.payload[start_index + 1 : start_index + 2].hex(), 16
        )

        if self.payload[start_index + 2 : start_index + 3] != b" ":
            raise ValueError("stack count terminator not found in item payload")

        return start_index + 3

    def __parse_item_properties(self, start_index):
        end_index = start_index

        property_start = self.payload.find(H_ITEM_PROPERTY, start_index)
        while property_start != -1:
            end_index = self.__parse_item_property(property_start)
            property_start = self.payload.find(H_ITEM_PROPERTY, end_index)

        return end_index

    def __parse_item_property(self, start_index):
        property_name_end = self.payload.find(
            b"\x10",
            start_index + len(H_ITEM_PROPERTY),
        )

        property_name = self.payload[
            start_index + len(H_ITEM_PROPERTY) : property_name_end
        ].decode("utf-8")

        # payload[property_name_end:property_name_end + 1] is a delimiter between the name and the value (\x10)

        property_value = int(
            self.payload[property_name_end + 1 : property_name_end + 2].hex(), 16
        )

        x = property_name_end + 2

        # If the value is negative, it is represented as a 2's complement
        if self.payload[x : x + 1] == b"\xff":
            property_value = property_value - 256

            # consume extra bytes when 2's complement is used
            while self.payload[x : x + 1] == b"\xff":
                x += 1
            if self.payload[x : x + 1] == b"\x01":
                x += 1

        # save the property data in the properties dictionary
        self.properties[property_name] = property_value

        next_property_start = self.payload.find(H_ITEM_PROPERTY, x + 1)

        return next_property_start if next_property_start != -1 else x

    def __parse_loot_state(self, start_index):
        if self.payload[start_index : start_index + 1] == b"\x58":
            logger.debug("loot state present.")
            self.loot_state = loot_state_str(
                int(self.payload[start_index + 1 : start_index + 2].hex(), 16)
            )
            return start_index + 2
        else:
            logger.debug("loot state not present.")
            self.loot_state = None
            return start_index

    def __parse_found_by(self, start_index):
        price_start = self.payload.find(b"\x18", start_index)

        if self.payload[start_index : start_index + 3].hex() == "60016a":
            logger.debug("found by present.")

            x = start_index + 3
            # Consume bytes until reaching an alphanumeric character
            while x < price_start and not self.payload[x : x + 1].isalnum():
                x += 1

            # Consume bytes until reaching a non alphanumeric character
            y = x
            while y < price_start and self.payload[y : y + 1].isalnum():
                y += 1

            self.found_by_name = self.payload[x:y].decode("utf-8")

            self.found_by_tag = self.payload[y + 1 : price_start].decode("utf-8")

            return price_start
        else:
            logger.debug("found by not present.")
            return start_index

    def __parse_price(self, start_index):
        if self.payload[start_index : start_index + 1] != b"\x18":
            logger.debug(
                "price not found where expected: trying to consume some extra unknown bytes"
            )
            start_index = self.payload.find(b"\x18", start_index)

            if start_index == -1:
                raise ValueError("price not found in item payload")

        price_end = self.payload.find(b"\x20", start_index)
        if price_end == -1:
            raise ValueError("price end not found in item payload")

        self.price = vlq_decode_little_endian(self.payload[start_index + 1 : price_end])

        return price_end

    def __parse_ts(self, start_index):
        ms = vlq_decode_little_endian(self.payload[start_index + 1 : start_index + 6])
        self.expiry_ts = datetime.now() + timedelta(milliseconds=ms)
        return start_index + 6

    def __parse_sold_by(self, start_index):
        sold_by_end = self.payload.find(b"\x12", start_index)

        # first 2 bytes are unknown but resolve to characters so we skip those manually
        x = start_index + 2

        # consume any extra unknown bytes until we reach an alphanumeric characters
        while x < sold_by_end and not self.payload[x : x + 1].isalnum():
            x += 1

        self.sold_by_name = self.payload[x:sold_by_end].decode("utf-8")

        # self.payload[sold_by_end:sold_by_end + 1] is a 1 byte separator ( potentially unknown data )

        # consume bytes to find the first non-alphanumeric character
        y = sold_by_end + 2
        while (
            y < len(self.payload)
            and self.payload[y : y + 1].isalnum()
            or self.payload[y : y + 1] == b"#"
        ):
            y += 1

        self.sold_by_tag = self.payload[sold_by_end + 2 : y].decode("utf-8")

        leaderboard_start = self.payload.find(H_LEADERBOARD_RANK, y)

        if leaderboard_start == -1:
            logger.debug("leaderboard rank not found.")
            return start_index

        self.sold_by_leaderboard_rank = self.payload[
            leaderboard_start + len(H_LEADERBOARD_RANK) :
        ].decode("utf-8")

        return len(self.payload)

    def dict(self):
        return {
            "header_bytes": self.header_bytes.hex(),
            "name": self.name,
            "rarity": self.rarity,
            "stack_count": self.stack_count,
            "properties": self.properties,
            "loot_state": self.loot_state,
            "found_by_name": (
                self.found_by_name if hasattr(self, "found_by_name") else None
            ),
            "found_by_tag": (
                self.found_by_tag if hasattr(self, "found_by_tag") else None
            ),
            "sold_by_name": self.sold_by_name,
            "sold_by_tag": self.sold_by_tag,
            "sold_by_leaderboard_rank": (
                self.sold_by_leaderboard_rank
                if hasattr(self, "sold_by_leaderboard_rank")
                else None
            ),
            "price": self.price,
            "expiry_ts": self.expiry_ts.isoformat(),
        }


class MarketplaceResponse:
    def __init__(self, payload: bytearray):
        self.payload = payload
        self.items = []
        self.__validate()
        self.__parse()

    def __parse(self):
        # there are 22 currently unknown bytes at the start of each item.
        UNKNOWN_BYTE_COUNT = 22

        # unknown 2 bytes to start the message
        self.header_bytes = self.payload[:2]

        # self.payload[2:6] is the marketplace response header
        self.item_count = 0

        # Convert the search string to bytes
        item_start = self.payload.find(H_ITEM_ID, 6)

        if item_start != -1:
            item_start -= UNKNOWN_BYTE_COUNT

        while item_start != -1:
            next_item_start = self.payload.find(
                H_ITEM_ID, item_start + UNKNOWN_BYTE_COUNT + len(H_ITEM_ID)
            )
            if next_item_start == -1:
                # no more items after this one
                break

            self.items.append(
                Item(self.payload[item_start : next_item_start - UNKNOWN_BYTE_COUNT])
            )

            # prep the next loop
            item_start = next_item_start - UNKNOWN_BYTE_COUNT

        footer_start, page_number_size, total_pages_size = calculate_footer(
            self.payload
        )

        if item_start != -1:
            self.items.append(Item(self.payload[item_start:footer_start]))

        self.page_number = vlq_decode_little_endian(
            self.payload[footer_start + 1 : footer_start + 1 + page_number_size]
        )

        self.total_pages = vlq_decode_little_endian(self.payload[-total_pages_size:])

    def __validate(self):
        if not self.payload:
            raise ValueError("Payload cannot be None")

        if not begins_marketplace_response(self.payload):
            raise ValueError("Payload does not begin with marketplace response header")

        if not ends_marketplace_response(self.payload):
            raise ValueError("Payload does not end with marketplace response footer")

        return True

    def dump(self):
        return json.dumps(
            {
                "items": [item.dict() for item in self.items],
                "page_number": self.page_number,
                "total_pages": self.total_pages,
            },
            indent=4,
        )


def begins_marketplace_response(payload: bytearray) -> bool:
    """
    Checks if a payload begins with the marketplace response header.
    """
    return payload is not None and payload[2:6].hex() == MARKETPLACE_RESPONSE_HEADER


# TODO: when invoking this message with a partial payload,
# it could potentially be a subset of the end bytes causing this to return an incorrect value
def ends_marketplace_response(payload: bytearray) -> bool:
    """
    Checks if the payload contains the end bytes of a marketplace response.
    The expected end bytes are:
    - 1 byte - 0x10
    - 1-3 bytes representing the page number
    - 1 byte - 0x18
    - 1-3 bytes representing the total pages

    returns true if the payload could represent the end of a marketplace response
    """
    if payload is None:
        return False

    if len(payload.hex()) < 8:  # Minimum length to contain the pattern
        return False

    # Check for the end pattern
    # This isn't a perfect solution, but it should work for now
    # we try different byte sizes for page number and total pages until something fits the expected pattern
    # certain page numbers or total page counts containing b'10' or b'18' could cause false positives
    for i in range(0, 3):  # Page number can be 1-3 bytes
        for j in range(0, 3):  # Total pages can be 1-3 bytes
            x1 = -(4 + (i + j))
            y1 = -(3 + (i + j))

            x2 = -(2 + j)
            y2 = -(1 + j)

            if payload[x1:y1] == b"\x10" and payload[x2:y2] == b"\x18":
                return True

    return False


def calculate_footer(payload):
    """
    Checks if the payload contains the end bytes of a marketplace response.
    The expected end bytes are:
    - 1 byte - 0x10
    - 1-3 bytes representing the page number
    - 1 byte - 0x18
    - 1-3 bytes representing the total pages

    returns the index of the start of the footer and the size of the page number and total pages
    """
    if payload is None:
        return None

    # Check for the pattern at the end of the payload
    if len(payload) < 8:  # Minimum length to contain the pattern
        return None

    # Check for the end pattern
    for i in range(0, 3):  # Page number can be 1-3 bytes
        for j in range(0, 3):  # Total pages can be 1-3 bytes
            x1 = -(4 + (i + j))
            y1 = -(3 + (i + j))

            x2 = -(2 + j)
            y2 = -(1 + j)

            if payload[x1:y1] == b"\x10" and payload[x2:y2] == b"\x18":
                return (x1, i + 1, j + 1)

    return None


def loot_state_str(loot_state):
    if loot_state is None:
        return "None"

    if loot_state == 2:
        return "Looted"
    if loot_state == 3:
        return "Handled"

    return "Unknown"


def rarity_str(rarity):
    if rarity is None:
        return "Common"
    if rarity == "1001":
        return "Poor"
    if rarity == "2001":
        return "Common"
    if rarity == "3001":
        return "Uncommon"
    if rarity == "4001":
        return "Rare"
    if rarity == "5001":
        return "Epic"
    if rarity == "6001":
        return "Legendary"
    if rarity == "7001":
        return "Unique"

    return "Unknown"
