package com.findus.packet

/**
 * The canonical reference vector shared across Python, Swift and Kotlin.
 * All three must agree on this exact packing; the JVM test enforces it.
 */
object CanonicalVectors {

    val referencePacket = PacketV2(
        pktType = PacketType.CACHED_MULE_BURST.value,
        sosId = 0x7A5,
        hopCount = 3,
        baroDiff = -5,
        flags = Flags.MULE_STORE_FORWARD or Flags.VISUAL_RUNWAY,
        epoch = 9,
        age = AgeBucket.UNDER_5MIN.value,
        reserved = ReservedBits.SECONDARY_PHY,
        envelopeMac = 0x8F42,
    )

    const val EXPECTED_HEX = "17a53ee2998f42"
    const val EXPECTED_BITS =
        "00010111101001010011111011100010100110011000111101000010"

    fun hex(raw: ByteArray): String = raw.joinToString("") { "%02x".format(it) }

    fun verify(): Boolean =
        hex(referencePacket.pack()) == EXPECTED_HEX &&
            referencePacket.toBitString() == EXPECTED_BITS
}
