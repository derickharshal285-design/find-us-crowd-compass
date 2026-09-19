plugins {
    kotlin("jvm") version "1.9.20"
    kotlin("android") version "1.9.20"
}

group = "com.findus"
version = "1.0.0"

repositories {
    mavenCentral()
    google()
}

dependencies {
    implementation(kotlin("stdlib"))
    // For HMAC-SHA256 on Android
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
}

// Java 11 compatibility
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile> {
    kotlinOptions {
        jvmTarget = "11"
    }
}