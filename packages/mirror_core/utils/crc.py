def crc16_ccitt(data: bytes) -> int:
    """
    Calculate CRC-16-CCITT (poly 0x1021) for data.
    Matches standard implementation used in embedded systems.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc
