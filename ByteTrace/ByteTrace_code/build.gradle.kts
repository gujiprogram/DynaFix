import com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar

plugins {
    id("com.github.johnrengelman.shadow") version "7.0.0"
    kotlin("jvm") version "1.9.23"
}

// Remove personal group information
group = "anonymous"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

dependencies {
    implementation("io.github.oshai:kotlin-logging-jvm:5.1.0")
    implementation("org.apache.logging.log4j:log4j-api:2.20.0")
    implementation("org.slf4j:slf4j-log4j12:2.0.10")
    implementation("com.google.code.gson:gson:2.11.0")
    implementation("org.ow2.asm:asm:9.5")
    implementation("org.ow2.asm:asm-commons:9.5")
    testImplementation("org.jetbrains.kotlin:kotlin-test")
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
    jvmToolchain(8)
}

// Configure ShadowJar task to generate Fat JAR with anonymous manifest
tasks.named<ShadowJar>("shadowJar") {
    // Set output JAR file name
    archiveFileName.set("ByteTrace.jar")

    // Configure manifest attributes with anonymous Premain-Class
    manifest {
        attributes(
            "Premain-Class" to "anonymous.DetectAgent",
            "Can-Redefine-Classes" to "true",
            "Can-Retransform-Classes" to "true"
        )
    }

    // Merge all dependencies into the Fat JAR
    mergeServiceFiles()
}

// Ensure shadowJar runs before build
tasks.build {
    dependsOn(tasks.shadowJar)
}
