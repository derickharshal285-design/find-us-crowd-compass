package com.findus.packet

/**
 * Systematic Hamming(7,4) FEC — nibble-wise encoding/decoding
 * 14 nibbles × 7 bits = 98 code bits + 6 pad bits = 104 bits = 13 bytes
 */
object HammingFEC {

    /** Encodes 7-byte raw payload (14 nibbles) into 13-byte coded frame */
    fun encode(raw: ByteArray): ByteArray {
        require(raw.size == 7) { "Expected 7 raw bytes, got ${raw.size}" }

        val nibbles = mutableListOf<Int>()
        for (b in raw) {
            nibbles.add((b shr 4) and 0x0F)
            nibbles.add(b.toInt() and 0x0F)
        }

        var total = 0L
        for (n in nibbles) {
            total = (total shl 7) or encodeNibble(n.toInt())
        }
        total = total shl 6  // 6 trailing zero padding bits

        // Convert to 13-byte big-endian array
        val result = ByteArray(13)
        for (i in 12 downTo 0) {
            result[i] = (total and 0xFFL).toByte()
            total = total shr 8
        }
        return result
    }

    /** Decodes 13-byte coded frame back into 7-byte raw payload.
     * Corrects any 1-bit error per nibble block (up to 14 bit errors across frame).
     * Returns Pair(rawBytes, totalErrorsCorrected)
     */
    fun decode(coded: ByteArray): Pair<ByteArray, Int> {
        require(coded.size == 13) { "Expected 13 coded bytes, got ${coded.size}" }

        // Load as 104-bit integer
        var total = 0L
        for (b in coded) {
            total = (total shl 8) or (b.toInt().toLong() and 0xFFL)
        }
        total = total shr 6  // Remove 6 padding bits

        // Extract 14 blocks of 7 bits (LSB first, then reverse)
        val blocks = mutableListOf<Int>()
        repeat(14) {
            blocks.add((total and 0x7FL).toInt())
            total = total shr 7
        }
        blocks.reverse()

        // Decode each nibble
        val decodedNibbles = mutableListOf<Int>()
        var totalCorrected = 0
        for (b in blocks) {
            val (d, err) = decodeNibble(b)
            decodedNibbles.add(d)
            totalCorrected += err
        }

        // Reassemble 7 bytes from 14 nibbles
        val raw = ByteArray(7)
        for (i in 0..6) {
            raw[i] = ((decodedNibbles[2 * i] shl 4) or decodedNibbles[2 * i + 1]).toByte()
        }
        return Pair(raw, totalCorrected)
    }

    private fun encodeNibble(d: Int): Int {
        val d1 = (d shr 3) and 1
        val d2 = (d shr 2) and 1
        val d3 = (d shr 1) and 1
        val d4 = d and 1
        val p1 = d1 xor d2 xor d4
        val p2 = d1 xor d3 xor d4
        val p3 = d2 xor d3 xor d4
        return (d1 shl 6) or (d2 shl 5) or (d3 shl 4) or (d4 shl 3) or (p1 shl 2) or (p2 shl 1) or p3
    }

    private fun decodeNibble(c: Int): Pair<Int, Int> {
        val r1 = (c shr 6) and 1
        val r2 = (c shr 5) and 1
        val r3 = (c shr 4) and 1
        val r4 = (c shr 3) and 1
        val r5 = (c shr 2) and 1
        val r6 = (c shr 1) and 1
        val r7 = c and 1

        val s1 = r1 xor r2 xor r4 xor r5
        val s2 = r1 xor r3 xor r4 xor r6
        val s3 = r2 xor r3 xor r4 xor r7
        val syndrome = (s1 shl 2) or (s2 shl 1) or s3

        var corrected = c
        var err = 0
        if (syndrome != 0) {
            val bitToFlip = when (syndrome) {
                1 -> 0
                2 -> 1
                3 -> 4
                4 -> 2
                5 -> 5
                6 -> 6
                7 -> 3
                else -> -1
            }
            if (bitToFlip >= 0) {
                corrected = corrected xor (1 shl bitToFlip)
                err = 1
            }
        }
        return Pair((corrected shr 3) and 0x0F, err)
    }
}