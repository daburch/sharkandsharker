def vlq_decode_little_endian_hex(hex_byte_sequence):
    """
    decode a variable length quantity integer (VLQ) from a hex byte sequence
    """
    value = 0
    shift = 0

    byte_sequence = bytes.fromhex(hex_byte_sequence.decode("utf-8"))

    for byte in byte_sequence:
        byte_value = byte

        # Check if the MSB is set (indicating continuation)
        if byte_value & 0x80:
            value |= (byte_value & 0x7F) << shift
            shift += 7
        else:
            value |= byte_value << shift
            return int(value)


def vlq_decode_little_endian(byte_sequence):
    """
    decode a variable length quantity integer (VLQ) from a hex byte sequence
    """
    value = 0
    shift = 0

    for byte in byte_sequence:
        byte_value = byte

        # Check if the MSB is set (indicating continuation)
        if byte_value & 0x80:
            value |= (byte_value & 0x7F) << shift
            shift += 7
        else:
            value |= byte_value << shift
            return int(value)
