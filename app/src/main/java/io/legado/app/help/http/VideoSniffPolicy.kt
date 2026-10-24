package io.legado.app.help.http

/**
 * 视频嗅探的纯策略与脚本（从 `BackstageWebView` 剥离，见 G-38 单文件行数门禁）。
 *
 * 只放**无副作用**的判定与字符串常量：命中可交付口径 [isDeliverableHit] 与
 * 播放页轻推脚本 [PLAY_NUDGE_JS]。会话生命周期仍由 BackstageWebView 负责。
 */
object VideoSniffPolicy {

    /** HLS 分片（`.ts`）不是可独立播放的流，必须只入候选缓冲 */
    fun isTsSegment(url: String): Boolean =
        url.substringBefore('?').lowercase().endsWith(".ts")

    /**
     * 命中候选是否可交付给上层。
     *
     * 两条排除（真机 2026-10-24 铁证）：
     * ① `.ts` 分片：ExoPlayer 需 m3u8 主索引，分片不能单独播放；
     * ② 命中 URL 与会话目标页相同：那是页面自身的请求（主框架/同址资源）。旧实现交付它 →
     *    上层判「等于原URL ⇒ null」并**立即 destroy 会话**（实测第 5ms），轻推脚本与
     *    `window.__videoUrls__` 读取全部来不及执行 ⇒ 缓存逐集必失败、播放黑屏。
     */
    fun isDeliverableHit(hitUrl: String, sessionUrl: String?): Boolean {
        return hitUrl != sessionUrl && !isTsSegment(hitUrl)
    }

    /**
     * 嗅探候选的**形态分类**（诊断用，只产出计数，不暴露 URL 内容）。
     *
     * 用途：当「拦截计数只有页面自身、video 有 src 但 readyState=0」时，需要区分两类根因：
     * - `blobOrMse > 0` ⇒ 播放器走 MSE（hls.js 等），真实流地址只会在分片请求里；
     * - `blobOrMse == 0 && http > 0 && matched == 0` ⇒ 直链 URL 形态不匹配源正则。
     */
    data class CandidateShape(
        val total: Int,
        val http: Int,
        val blobOrMse: Int,
        val mime: Int,
        val matched: Int
    )

    fun classifyCandidates(urls: List<String>, isMatch: (String) -> Boolean): CandidateShape {
        return CandidateShape(
            total = urls.size,
            http = urls.count { it.startsWith("http") },
            blobOrMse = urls.count { it.startsWith("__MSE__") || it.startsWith("blob:") },
            mime = urls.count { it.startsWith("__MSE_MIME__") },
            matched = urls.count(isMatch)
        )
    }

    /**
     * 播放页「自动播放轻推」脚本（2026-10-24 真机实证新增）。
     *
     * 背景：大量采集站播放页必须**先触发播放**才发 m3u8 请求。后台嗅探没有用户手势，
     * 只挂 fetch/XHR 钩子会 0 命中（实测 160 次嗅探 0 命中 ⇒ 播放/缓存双双失败）。
     * 脚本只在播放器上下文动作（muted + playsinline + play() + 点击 video 及其可点击祖先），
     * 点击限流 ≤3 次防误触广告；失败静默，不影响原嗅探链。
     *
     * 输出（诊断用，仅计数/长度，不含页面文本）：
     * - `v` video 元素数、`p` play() 成功数、`c` 点击次数、`s` 有 src 的 video 数
     * - `ifr` iframe 数、`rd` readyState、`bl` body HTML 长度、`sc` script 数、`ms` 含媒体串的 script 数
     */
    val PLAY_NUDGE_JS = """
        (function(){
          var out={v:0,p:0,c:0,s:0,ifr:0,rd:0,cls:'',err:''};
          try{
            var vs=document.querySelectorAll('video');
            out.v=vs.length;
            for(var i=0;i<vs.length;i++){
              var v=vs[i];
              try{ v.muted=true; v.setAttribute('playsinline',''); var pr=v.play(); if(pr&&pr.catch){pr.catch(function(){});} out.p++; }catch(e){}
              // 点击 video 自身与其可点击祖先（≤3 层）：大量播放器把 play 绑在外层容器上
              try{ v.click(); }catch(e){}
              try{
                var p=v.parentElement;
                for(var k=0;k<3&&p;k++){ p.click(); p=p.parentElement; }
              }catch(e){}
              try{
                if((v.currentSrc||v.src)&&String(v.currentSrc||v.src).length>0) out.s++;
                out.rd=Math.max(out.rd, v.readyState||0);
                if(i===0&&v.className) out.cls=String(v.className).slice(0,40);
              }catch(e){}
            }
            // 播放器可能延迟挂载：命中常见按钮类名即点（限流 ≤3）
            var all=document.querySelectorAll('[class*="play"],[id*="play"],.vjs-big-play-button,button');
            var n=0;
            for(var j=0;j<all.length&&n<3;j++){
              var el=all[j];
              if(!el) continue;
              var inPlayer=false;
              try{
                inPlayer=!!( (el.querySelector&&el.querySelector('video')) ||
                             (el.closest&&el.closest('video')) ||
                             (el.parentElement&&el.parentElement.querySelector('video')) ||
                             (el.className&&/play/i.test(String(el.className))) );
              }catch(e){}
              if(inPlayer){ try{ el.click(); n++; out.c=n; }catch(e){} }
            }
            try{ out.ifr=document.querySelectorAll('iframe').length; }catch(e){}
            // 结构性诊断（只统计数量/长度，不含页面文本）：判断「页面根本没渲染播放器」
            // 与「播放器在但未发流」这两类根因——真机 v=0/ifr=0/拦截=1 时需要此证据
            try{
              out.bl=document.body?document.body.innerHTML.length:0;
              var ss=document.querySelectorAll('script');
              out.sc=ss.length;
              var hit=0;
              for(var q=0;q<ss.length;q++){
                var t=ss[q].textContent||'';
                if(t.indexOf('m3u8')>=0||t.indexOf('.mp4')>=0) hit++;
              }
              out.ms=hit;
              out.dv=document.querySelectorAll('div').length;
            }catch(e){}
          }catch(e){ out.err=String(e).slice(0,60); }
          return JSON.stringify(out);
        })();
    """.trimIndent()
}
