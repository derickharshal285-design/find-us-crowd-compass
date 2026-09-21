package com.findus.crowdcompass.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.findus.crowdcompass.engine.IncidentSession
import kotlinx.coroutines.flow.first

private val Context.dataStore by preferencesDataStore(name = "findus")

/** Persists the shared incident link so a restart resumes the same incident. */
class IncidentStore(private val context: Context) {

    private val key = stringPreferencesKey("incident_link")
    private val identity = stringPreferencesKey("install_key_b64")

    suspend fun saveLink(link: String, installKeyB64: String) {
        context.dataStore.edit { prefs ->
            prefs[key] = link
            prefs[identity] = installKeyB64
        }
    }

    suspend fun load(): Joined? {
        val prefs = context.dataStore.data.first()
        val link = prefs[key] ?: return null
        val install = prefs[identity]
            ?: return null
        val session = runCatching { IncidentSession.parseLink(link) }.getOrNull() ?: return null
        return Joined(session, install)
    }

    suspend fun clear() {
        context.dataStore.edit { it.remove(key); it.remove(identity) }
    }

    data class Joined(val session: IncidentSession, val installKeyB64: String)
}