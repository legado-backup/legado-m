plugins {
    kotlin("jvm") version "2.1.0"
    application
}

application {
    mainClass.set("io.legado.ruleengine.RuleEngineServerKt")
}

repositories {
    mavenCentral()
    maven { url = uri("https://jitpack.io") }
}

dependencies {
    // Rhino JS 引擎（Legado 锁定版本 1.8.1）
    implementation("org.mozilla:rhino:1.8.1")

    // jsoup HTML 解析器（Legado 锁定版本 1.16.2）
    implementation("org.jsoup:jsoup:1.16.2")

    // JsoupXpath（@XPath: 规则解析，与 Legado 版本一致）
    implementation("cn.wanghaomiao:JsoupXpath:2.5.3")

    // JSONPath（@Json: 和 $. 规则解析）
    implementation("com.jayway.jsonpath:json-path:2.10.0")

    // Gson（JSON 序列化，与 Legado 版本一致）
    implementation("com.google.code.gson:gson:2.13.2")

    // OkHttp（HTTP 请求，与 Legado 版本一致）
    implementation("com.squareup.okhttp3:okhttp:5.3.2")

    // Hutool 加密（与 Legado 版本一致）
    implementation("cn.hutool:hutool-crypto:5.8.22")

    // Apache Commons Text（字符串处理）
    implementation("org.apache.commons:commons-text:1.13.1")

    // chinese-transfer（繁简转换，与 Legado 版本一致）
    implementation("com.github.liuyueyi.quick-chinese-transfer:quick-transfer-core:0.2.17")

    // Kotlin 协程
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.10.2")

    // 测试框架（JUnit 5）
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.1")
    testImplementation("org.junit.jupiter:junit-jupiter-api:5.10.1")
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile> {
    kotlinOptions.freeCompilerArgs += "-Xwhen-guards"
}

tasks.named<Test>("test") {
    useJUnitPlatform()
}

tasks.register<Jar>("fatJar") {
    archiveBaseName.set("legado-jvm")
    archiveClassifier.set("")
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    manifest { attributes["Main-Class"] = "io.legado.ruleengine.RuleEngineServerKt" }
    from(configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) })
    with(tasks.jar.get())
}
