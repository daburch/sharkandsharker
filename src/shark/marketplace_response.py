import logging
import json

from utils import vlq_decode_little_endian

from constants import MARKETPLACE_RESPONSE_HEADER, H_ITEM_ID

logger = logging.getLogger(__name__)


class MarketplaceResponse:
    def __init__(self, payload: bytearray):
        self.payload = payload
        self.items = []
        self.__validate()
        self.__parse()

    def __parse(self):
        # unknown 2 bytes to start the message
        self.header_bytes = self.payload[:2]

        # self.payload[2:6] is the marketplace response header
        self.item_count = 0

        # Convert the search string to bytes
        item_start = self.payload.find(H_ITEM_ID, 6)

        # there are 20 currently unknown bytes at the start of each item.
        if item_start != -1:
            item_start -= 20

        while item_start != -1:
            next_item_start = self.payload.find(
                H_ITEM_ID, item_start + 20 + len(H_ITEM_ID)
            )
            if next_item_start == -1:
                # no more items after this one
                break

            # TODO: create an Item instance
            self.item_count += 1

            # prep the next loop
            item_start = next_item_start - 20

        footer_start, page_number_size, total_pages_size = calculate_footer(
            self.payload
        )

        if item_start != -1:
            # TODO: create the final Item instance
            self.item_count += 1

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
                "item_count": self.item_count,
                "page_number": self.page_number,
                "total_pages": self.total_pages,
            },
            indent=4,
        )
        logger.info(f"Item count: {self.item_count}")
        logger.info(f"Page number: {self.page_number}")
        logger.info(f"Total pages: {self.total_pages}")


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
