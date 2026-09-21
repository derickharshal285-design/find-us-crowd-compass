package com.findus.crowdcompass.engine

import java.security.MessageDigest
import java.util.Base64
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Incident session port of core/security.py: shared key derived from the
 * incident link, 8-byte canonical HMAC-SHA256, incident-scoped pseudonym.
 */
class IncidentSession(val incidentId: String, val salt: ByteArray,
                      var linkTtl: Int = 8, var linkLife: Double = 900.0) {

    val key: ByteArray = hmac("HmacSHA256", hmac("HmacSHA256",
        INCIDENT_FIXED_KEY.toByteArray(), msgBytes()), HKDF_INFO)
    val authKey: ByteArray = hmac("HmacSHA256", key, AUTH_INFO)

    private fun msgBytes(): ByteArray {
        val out = ByteArrayOutputStreamSafe()
        out.write(incidentId.toByteArray(Charsets.UTF_8))
        out.write(0)
        out.write(salt)
        return out.toByteArray()
    }

    fun mac(pkt: RelayPacket): ByteArray {
        val full = hmac("HmacSHA256", authKey, canonicalFields(pkt))
        return full.copyOf(MAC_LENGTH)
    }

    fun verify(pkt: RelayPacket): Boolean {
        pkt.authTag ?: return false
        val expected = mac(pkt)
        return MessageDigest.isEqual(expected, pkt.authTag.copyOf(MAC_LENGTH))
    }

    fun attach(pkt: RelayPacket): RelayPacket =
        pkt.copy(authTag = mac(pkt))

    fun pseudonym(installKey: ByteArray): String {
        val raw = hmac("HmacSHA256", installKey,
            PSEUDOOM_INFO + byteArrayOf(0) + incidentId.toByteArray(Charsets.UTF_8))
        return Base64.getUrlEncoder().withoutPadding().encodeToString(raw.copyOf(6))
    }

    fun toLink(ttlHops: Int = 8, lifespan: Double = 900.0): String {
        val saltB64 = Base64.getUrlEncoder().withoutPadding().encodeToString(salt)
        val idBytes = incidentId.toByteArray(Charsets.UTF_8)
        val payloadBytes = ByteArray(2 + idBytes.size + salt.size)
        payloadBytes[0] = (idBytes.size ushr 8).toByte()
        payloadBytes[1] = idBytes.size.toByte()
        idBytes.copyInto(payloadBytes, 2)
        salt.copyInto(payloadBytes, 2 + idBytes.size)
        val payload = Base64.getUrlEncoder().withoutPadding().encodeToString(payloadBytes)
        return "$LINK_PREFIX$payload?salt=$saltB64&ttl=$ttlHops&life=${lifespan.toInt()}"
    }

    companion object {
        const val MAC_LENGTH = 8
        const val LINK_PREFIX = "incident://"
        const val INCIDENT_FIXED_KEY = "CROWD-COMPASS/INCIDENT"
        val HKDF_INFO = "crowd-compass/incident-session-v1".toByteArray()
        val AUTH_INFO = "crowd-compass/gradient-mac-v1".toByteArray()
        val PSEUDOOM_INFO = "crowd-compass/incident-pseudonym-v1".toByteArray()

        fun makeSession(incidentId: String, salt: ByteArray = randomSalt()): IncidentSession =
            IncidentSession(incidentId, salt)

        fun randomSalt(): ByteArray {
            val rng = java.security.SecureRandom()
            return ByteArray(16).also { rng.nextBytes(it) }
        }

        fun parseLink(link: String): IncidentSession {
            if (!link.startsWith(LINK_PREFIX)) {
                throw IllegalArgumentException("not an incident link")
            }
            val rest = link.removePrefix(LINK_PREFIX)
            val query = rest.substringAfter('?', "")
            val bodyB64 = rest.substringBefore('?')
            val padded = bodyB64 + "=".repeat((4 - bodyB64.length % 4) % 4)
            val decoded = Base64.getUrlDecoder().decode(padded)
            if (decoded.size < 3) throw IllegalArgumentException("malformed link payload")
            val n = ((decoded[0].toInt() and 0xFF) shl 8) or (decoded[1].toInt() and 0xFF)
            if (2 + n > decoded.size) throw IllegalArgumentException("malformed link payload")
            val incidentId = String(decoded, 2, n, Charsets.UTF_8)
            val salt = decoded.copyOfRange(2 + n, decoded.size)
            val session = IncidentSession(incidentId, salt)
            session.linkTtl = queryParam(query, "ttl", 8) { it.toIntOrNull() ?: 8 }
            session.linkLife = queryParam(query, "life", 900.0) { it.toDoubleOrNull() ?: 900.0 }
            return session
        }

        private inline fun <T> queryParam(query: String, key: String, default: T, conv: (String) -> T): T {
            for (part in query.split("&")) {
                val kv = part.split("=", limit = 2)
                if (kv.size == 2 && kv[0] == key) return conv(kv[1])
            }
            return default
        }

        private fun hmac(algo: String, key: ByteArray, data: ByteArray): ByteArray {
            val m = Mac.getInstance(algo)
            m.init(SecretKeySpec(key, algo))
            return m.doFinal(data)
        }
    }

    /** Canonical on-wire fields: U8 mtype | 16B event | 8B sender | U16 ver | U8 hop | U8 ttl | U32 ts. */
    fun canonicalFields(pkt: RelayPacket): ByteArray {
        val ts = canonTs(pkt.timestamp)
        return ByteBufferBE()
            .put(pkt.messageType.wire.toByte())
            .put(padId(pkt.eventId?.value.orEmpty(), 16))
            .put(padId(pkt.sender?.value.orEmpty(), 8))
            .putShort(pkt.sourceVersion.coerceIn(0, 0xFFFF).toShort())
            .put(pkt.hop.coerceIn(0, 0xFF).toByte())
            .put(pkt.ttl.coerceIn(0, 0xFF).toByte())
            .putInt(ts)
            .array()
    }

    private fun canonTs(t: Double): Int {
        if (t == Engine.TIME_NONE || t <= 0.0) return 0
        return Math.round(t - Engine.EPOCH).coerceIn(0, 0xFFFFFFFFL).toInt()
    }

    private fun padId(value: String, width: Int): ByteArray {
        val raw = value.toByteArray(Charsets.UTF_8)
        val out = ByteArray(width)
        for (i in 0 until minOf(raw.size, width)) out[i] = raw[i]
        return out
    }
}

/** Minimal big-endian byte writer to keep protocol + MAC byte-faithful. */
class ByteBufferBE {
    private val data = java.io.ByteArrayOutputStream()
    fun put(b: Byte): ByteBufferBE { data.write(b.toInt()); return this }
    fun put(bs: ByteArray): ByteBufferBE { data.write(bs); return this }
    fun putShort(v: Short): ByteBufferBE {
        data.write((v.toInt() ushr 8) and 0xFF); data.write(v.toInt() and 0xFF); return this
    }
    fun putInt(v: Int): ByteBufferBE {
        data.write((v ushr 24) and 0xFF); data.write((v ushr 16) and 0xFF)
        data.write((v ushr 8) and 0xFF); data.write(v and 0xFF); return this
    }
    fun array(): ByteArray = data.toByteArray()
}

class ByteArrayOutputStreamSafe {
    private val data = java.io.ByteArrayOutputStream()
    fun write(b: Int) { data.write(b) }
    fun write(bs: ByteArray) { data.write(bs) }
    fun toByteArray(): ByteArray = data.toByteArray()
}