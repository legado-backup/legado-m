package io.legado.app.help.source

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Assume.assumeTrue
import org.junit.Ignore
import org.junit.Test
import java.io.File
import java.nio.file.Files

/**
 * P0-S1 书源沙箱策略单测（分册 P0-source-security-hardening §9.1 T1-T10）
 *
 * 覆盖 BookSourceStorageScope（ns 稳定性）与 BookSourceFileAccessPolicy
 * （沙箱边界：归一放行/穿越拒绝/绝对路径内外/空路径/子树包含/符号链接逃逸）。
 * 纯 java.io 实现，纯 JVM 可测（internal 同 module 可见）。
 *
 * T8 符号链接逃逸：Windows 非特权环境无法创建 symlink，用 Assume 跳过并标注 L2 真机复验（E20）。
 */
class SourceSandboxPolicyTest {

    private val tempDirs = mutableListOf<File>()

    private fun newTempDir(prefix: String): File =
        Files.createTempDirectory(prefix).toFile().also { tempDirs.add(it) }

    @After
    fun tearDown() {
        tempDirs.forEach { dir ->
            kotlin.runCatching { dir.deleteRecursively() }
        }
        tempDirs.clear()
    }

    // ============ T1 namespace 稳定性 ============

    @Test
    fun namespace_isHex64AndStable() {
        val url = "https://source.example/A.json"
        val ns1 = BookSourceStorageScope.namespace(url)
        val ns2 = BookSourceStorageScope.namespace(url)
        val ns3 = BookSourceStorageScope.namespace("https://other.example/A.json")
        // 同 URL 稳定
        assertEquals(ns1, ns2)
        // 异 URL 必异
        assertNotEquals(ns1, ns3)
        // 64 位小写 hex
        assertEquals(64, ns1.length)
        assertTrue("ns 应为小写 hex: $ns1", ns1.all { it in '0'..'9' || it in 'a'..'f' })
    }

    // ============ T2 resolveSourceRoot 确定性 ============

    @Test
    fun resolveSourceRoot_isUnderCacheRootAndDeterministic() {
        val cacheRoot = newTempDir("p0sandboxRoot")
        val url = "https://source.example/B.json"
        val ns = BookSourceStorageScope.namespace(url)
        val root1 = BookSourceFileAccessPolicy.resolveSourceRoot(cacheRoot, url)
        val root2 = BookSourceFileAccessPolicy.resolveSourceRoot(cacheRoot, url)
        // 确定性：同 URL 两次解析一致
        assertEquals(root1.canonicalPath, root2.canonicalPath)
        // 位于缓存根内二级目录 source/{ns}
        assertTrue(root1.canonicalPath.startsWith(cacheRoot.canonicalPath + File.separator))
        assertEquals(
            File(cacheRoot, "source${File.separator}$ns").canonicalPath,
            root1.canonicalPath
        )
    }

    // ============ T3 相对路径归一放行 ============

    @Test
    fun resolvePath_relativeNormalizesWithinRoot() {
        val root = BookSourceFileAccessPolicy.resolveSourceRoot(newTempDir("p0sandboxRoot"), "u3")
        val target = BookSourceFileAccessPolicy.resolvePath(root, "a/../b.png")
        // a/../ 归一后仍在沙箱根内放行
        assertEquals(File(root, "b.png").canonicalPath, target.file.canonicalPath)
    }

    // ============ T4 父目录穿越拒绝 ============

    @Test
    fun resolvePath_parentTraversalRejected() {
        val root = BookSourceFileAccessPolicy.resolveSourceRoot(newTempDir("p0sandboxRoot"), "u4")
        try {
            BookSourceFileAccessPolicy.resolvePath(root, "../../x")
            fail("../../x 穿越应抛 SecurityException")
        } catch (expected: SecurityException) {
            // 预期：越界统一 SecurityException 不回退
        }
    }

    // ============ T5 绝对路径位于根内放行 ============

    @Test
    fun resolvePath_absoluteInsideRootAllowed() {
        val root = BookSourceFileAccessPolicy.resolveSourceRoot(newTempDir("p0sandboxRoot"), "u5")
        val inside = File(root, "sub${File.separator}f.png")
        val target = BookSourceFileAccessPolicy.resolvePath(root, inside.absolutePath)
        assertEquals(inside.canonicalPath, target.file.canonicalPath)
    }

    // ============ T6 绝对路径位于根外拒绝 ============
    // 偏差已修复（2026-09-01）：源实现 resolvePath else 分支依赖 File(root, path)，Windows JVM
    // 对绝对 child 为拼接语义不拒绝；已改为显式 file.isAbsolute 判定+根内校验（KDoc L20 声明对齐），
    // @Ignore 解除。
    @Test
    fun resolvePath_absoluteOutsideRootRejected() {
        val root = BookSourceFileAccessPolicy.resolveSourceRoot(newTempDir("p0sandboxRoot"), "u6")
        val outside = newTempDir("p0outside")
        val outsideFile = File(outside, "evil.png")
        try {
            BookSourceFileAccessPolicy.resolvePath(root, outsideFile.absolutePath)
            fail("根外绝对路径应抛 SecurityException")
        } catch (expected: SecurityException) {
        }
    }

    // ============ T7 空路径/根本身拒绝 ============

    @Test
    fun resolvePath_emptyOrRootRejected() {
        val root = BookSourceFileAccessPolicy.resolveSourceRoot(newTempDir("p0sandboxRoot"), "u7")
        listOf("", "/").forEach { path ->
            try {
                BookSourceFileAccessPolicy.resolvePath(root, path)
                fail("路径 \"$path\"（空或根本身）应抛 SecurityException")
            } catch (expected: SecurityException) {
            }
        }
    }

    // ============ T8 符号链接逃逸拒绝（Temp 目录模拟） ============

    @Test
    fun requireContainedTree_rejectsSymlinkEscape() {
        val cacheRoot = newTempDir("p0sandboxRoot")
        val root = BookSourceFileAccessPolicy.resolveSourceRoot(cacheRoot, "u8")
        // resolveSourceRoot 只构造不落盘：先建父链再建子树
        Files.createDirectories(root.toPath())
        val outside = newTempDir("p0outside")
        val sub = Files.createDirectory(root.toPath().resolve("sub")).toFile()
        // Windows 非特权环境可能无法创建符号链接：Assume 跳过
        val created = kotlin.runCatching {
            Files.createSymbolicLink(sub.toPath().resolve("link"), outside.toPath())
        }.isSuccess
        assumeTrue("环境不支持符号链接（Windows 需开发者模式/管理员），symlink 逃逸断言转入 L2 真机复验", created)
        // 登记平台差异（E20，勿改源码约束）：实现依赖 getCanonicalPath 跟随 symlink（POSIX 行为，
        // Android/Linux 生产环境成立）；实测 Windows JDK17 getCanonicalPath 不解析目录 symlink，
        // 本用例在该环境无法验证拒绝语义，转入 L2 真机复验。仅当 canonical 跟随 symlink 时执行断言。
        val canonicalResolvesLink = File(sub, "link").canonicalPath == outside.canonicalPath
        assumeTrue(
            "Windows JVM canonical 不解析目录符号链接，symlink 逃逸拒绝断言转入 L2 真机复验（E20）",
            canonicalResolvesLink
        )
        // 子树整体校验：link 指向根外目录，requireContainedTree 递归 canonical 化后应拒绝
        try {
            BookSourceFileAccessPolicy.requireContainedTree(root, sub)
            fail("子树内符号链接逃逸应抛 SecurityException")
        } catch (expected: SecurityException) {
        }
    }

    // ============ T9 子树包含放行 ============

    @Test
    fun requireContainedTree_allowsSubtree() {
        val cacheRoot = newTempDir("p0sandboxRoot")
        val root = BookSourceFileAccessPolicy.resolveSourceRoot(cacheRoot, "u9")
        val nested = File(root, "sub${File.separator}deep${File.separator}nested")
        assertTrue(nested.mkdirs())
        assertTrue(File(nested, "f.txt").createNewFile())
        // 全部位于根内：不抛
        BookSourceFileAccessPolicy.requireContainedTree(root, File(root, "sub"))
    }

    // ============ T10 相对路径语义（不含根前缀） ============

    @Test
    fun resolvePath_returnsRelativePathWithoutRootPrefix() {
        val root = BookSourceFileAccessPolicy.resolveSourceRoot(newTempDir("p0sandboxRoot"), "u10")
        val target = BookSourceFileAccessPolicy.resolvePath(root, "d${File.separator}f.png")
        val expectedRelative = "${File.separator}d${File.separator}f.png"
        assertEquals(expectedRelative, target.relativePath)
        // 不含根前缀：relativePath 仅以分隔符开头，非绝对路径
        assertFalse(target.relativePath.startsWith(root.canonicalPath))
    }
}
