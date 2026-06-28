package io.legado.app.utils

// 源码参照: app/src/main/java/io/legado/app/utils/StringUtils.kt
// 简化说明: 仅移植 toNumChapter 所需的 stringToInt/fullToHalf/chineseNumToInt/CHN_MAP | 已知上限: 未移植 dateConvert/halfToFull/wordCountFormat 等其他方法 | 升级路径: 按需移植其他方法
// 修复说明: 新建 StringUtils 仿真端，移植 stringToInt 链路，使 toNumChapter 与真机行为一致

@Suppress("unused")
object StringUtils {
    private val CHN_MAP: HashMap<Char, Int> by lazy {
        val map = HashMap<Char, Int>()
        var cnStr = "零一二三四五六七八九十"
        var c = cnStr.toCharArray()
        for (i in 0..10) {
            map[c[i]] = i
        }
        cnStr = "〇壹贰叁肆伍陆柒捌玖拾"
        c = cnStr.toCharArray()
        for (i in 0..10) {
            map[c[i]] = i
        }
        map['两'] = 2
        map['百'] = 100
        map['佰'] = 100
        map['千'] = 1000
        map['仟'] = 1000
        map['万'] = 10000
        map['亿'] = 100000000
        map
    }

    /**
     * 字符串全角转换为半角
     */
    fun fullToHalf(input: String): String {
        val c = input.toCharArray()
        for (i in c.indices) {
            if (c[i].code == 12288)
            //全角空格
            {
                c[i] = 32.toChar()
                continue
            }

            if (c[i].code in 65281..65374)
                c[i] = (c[i].code - 65248).toChar()
        }
        return String(c)
    }

    /**
     * 中文大写数字转数字
     */
    fun chineseNumToInt(chNum: String): Int {
        var result = 0
        var tmp = 0
        var billion = 0
        val cn = chNum.toCharArray()

        // "一零二五" 形式
        if (cn.size > 1 && chNum.matches("^[〇零一二三四五六七八九壹贰叁肆伍陆柒捌玖]$".toRegex())) {
            for (i in cn.indices) {
                cn[i] = (48 + CHN_MAP[cn[i]]!!).toChar()
            }
            return Integer.parseInt(String(cn))
        }

        // "一千零二十五", "一千二" 形式
        return kotlin.runCatching {
            for (i in cn.indices) {
                val tmpNum = CHN_MAP[cn[i]]!!
                when {
                    tmpNum == 100000000 -> {
                        result += tmp
                        result *= tmpNum
                        billion = billion * 100000000 + result
                        result = 0
                        tmp = 0
                    }

                    tmpNum == 10000 -> {
                        result += tmp
                        result *= tmpNum
                        tmp = 0
                    }

                    tmpNum >= 10 -> {
                        if (tmp == 0)
                            tmp = 1
                        result += tmpNum * tmp
                        tmp = 0
                    }

                    else -> {
                        tmp = if (i >= 2 && i == cn.size - 1 && CHN_MAP[cn[i - 1]]!! > 10)
                            tmpNum * CHN_MAP[cn[i - 1]]!! / 10
                        else
                            tmp * 10 + tmpNum
                    }
                }
            }
            result += tmp + billion
            result
        }.getOrDefault(-1)
    }

    /**
     * 字符串转数字
     */
    fun stringToInt(str: String?): Int {
        if (str != null) {
            val num = fullToHalf(str).replace("\\s+".toRegex(), "")
            return kotlin.runCatching {
                Integer.parseInt(num)
            }.getOrElse {
                chineseNumToInt(num)
            }
        }
        return -1
    }
}
