package com.findus.packet

import java.math.BigInteger

/**
 * Nibble-wise systematic Hamming (7,4) FEC — port of packet_v2.py.
 * 7 raw bytes (14 nibbles) -> 98 code bits + 6 pad = 104 bits = 13 bytes.
 * Corrects one bit per nibble (up to 14 simultaneous bit flips per frame).
 */
object HammingFEC {

    /** syndrome -> bit index to flip, or -1 when no error. Parity of packet_v2.py. */
    private val ERROR_BIT = intArrayOf(-1, 0, 1, 4, 2, 5, 6, 3)

    private fun encodeNibble(d: Int): Int {
        val d1 = (d shr 3) and 1
        val d2 = (d shr 2) and 1
        val d3 = (d shr 1) and 1
        val d4 = d and 1
        val p1 = d1 xor d2 xor d4
        val p2 = d1 xor d3 xor d4
        val p3 = d2 xor d3 xor d4
        return (d1 shl 6) or (d2 shl 5) or (d3 shl 4) or (d4 shl 3) or
            (p1 shl 2) or (p2 shl 1) or p3
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
        val flip = ERROR_BIT[syndrome]
        var code = c
        var corrected = 0
        if (flip >= 0) {
            code = code xor (1 shl flip)
            corrected = 1
        }
        return ((code shr 3) and 0x0F) to corrected
    }

    fun encode(raw7: ByteArray): ByteArray {
        require(raw7.size == 7) { "Expected 7 raw bytes, got ${raw7.size}" }
        var total = BigInteger.ZERO
        for (b in raw7) {
            for (nibble in intArrayOf((b.toInt() shr 4) and 0x0F, b.toInt() and 0x0F)) {
                total = total.shiftLeft(7)
                    .or(BigInteger.valueOf((encodeNibble(nibble) and 0x7F).toLong()))
            }
        }
        total = total.shiftLeft(6)
        return toFixedBytes(total, 13)
    }

    fun decode(coded13: ByteArray): Pair<ByteArray, Int> {
        require(coded13.size == 13) { "Expected 13 coded bytes, got ${coded13.size}" }
        var total = BigInteger(1, coded13).shiftRight(6)
        val blocks = IntArray(14)
        val mask = BigInteger.valueOf(0x7F)
        for (i in 0 until 14) {
            blocks[i] = total.and(mask).toInt()
            total = total.shiftRight(7)
        }
        blocks.reverse()
        val nibbles = IntArray(14)
        var corrected = 0
        for (i in 0 until 14) {
            val (d, err) = decodeNibble(blocks[i])
            nibbles[i] = d
            corrected += err
        }
        val raw = ByteArray(7)
        for (i in 0 until 7) {
            raw[i] = ((nibbles[2 * i] shl 4) or nibbles[2 * i + 1]).toByte()
        }
        return raw to corrected
    }

    private fun toFixedBytes(value: BigInteger, size: Int): ByteArray {
        val raw = value.toByteArray()
        val out = ByteArray(size)
        if (raw.size >= size) {
            System.arraycopy(raw, raw.size - size, out, 0, size)
        } else {
            System.arraycopy(raw, 0, out, size - raw.size, raw.size)
        }
        return out
    }
}
