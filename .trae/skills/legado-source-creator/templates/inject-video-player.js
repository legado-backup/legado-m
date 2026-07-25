// Legado WebView 视频播放器注入脚本
// 版本: V3.20260606.1
// 作者: Miss光头强
// 功能: 劫持已有播放器实例，优化缓冲+去广告
// 用途: webJs 注入脚本，IIFE 封装
//
// 更新日志:
// V3.20260606.1 - 13项核心优化:
//   1. 删除 Object.defineProperty(window.location,'href') 致命Bug
//   2. 删除 window.location.replace 覆盖致命Bug
//   3. 缓冲优化改为 destroy+recreate（替代改config）
//   4. 播放器检测算法重构为数据驱动（PLAYER_DEFS）
//   5. MutationObserver 限制范围（subtree:false）
//   6. 移除 setInterval(blockAdElements, 10000) 定时全量扫描
//   7. CSS transition 精确化（all→具体属性）
//   8. backdrop-filter 兼容降级（实色+@supports）
//   9. 白名单 URL 检测增强（路径分析）
//  10. 新增 XHR/Fetch 拦截获取视频 URL
//  11. 新增卡顿检测+自动降级
//  12. iframe 跨域访问优化（先检查同源）
//  13. 动态 meta refresh 处理

(function() {
    'use strict';

    // ============================================================
    // 配置对象
    // ============================================================
    var config = {
        // 缓冲优化配置
        buffer: {
            maxBufferLength: 180,        // 最大缓冲长度（秒）
            maxMaxBufferLength: 600,     // 最大最大缓冲长度（秒）
            maxBufferSize: 200 * 1024 * 1024, // 最大缓冲大小（200MB）
            backBufferLength: 180,       // 后缓冲长度（秒）
            maxBufferHole: 0.5,          // 最大缓冲空洞（秒）
            startFragPrefetch: true,     // 启用片段预加载
            capLevelToPlayerSize: false  // 不根据播放器大小限制码率
        },
        // 广告拦截配置
        adBlocker: {
            enabled: true,
            videoWhitelist: [
                'm3u8', 'mp4', 'webm', 'ogg', 'mkv', 'avi',
                'flv', 'ts', 'f4v', 'mov', 'wmv', '3gp',
                'video', 'media', 'play', 'stream', 'hls',
                'dash', 'cdn', 'vod', 'live', 'source'
            ],
            adKeywords: [
                'ad', 'ads', 'adv', 'advert', 'advertising',
                'banner', 'popup', 'popunder', 'preroll',
                'midroll', 'postroll', 'tracking', 'analytics',
                'doubleclick', 'googlesyndication', 'adservice',
                'adserver', 'adnxs', 'adsrvr', 'adroll'
            ],
            removePopups: true,
            blockRedirects: true
        },
        // 净化模式
        cleanMode: {
            enabled: true,
            removeComments: true,
            removeSocialWidgets: true,
            removeRelatedVideos: true
        },
        // 自动播放
        autoPlay: {
            enabled: true,
            muted: true,
            retryCount: 3,
            retryDelay: 1000
        },
        // 调试
        debug: {
            enabled: true,
            maxLogEntries: 200
        },
        // 卡顿检测
        stallDetection: {
            enabled: true,
            threshold: 3,       // 连续卡顿次数阈值
            windowMs: 5000      // 卡顿计数窗口（毫秒）
        }
    };

    // ============================================================
    // 日志系统
    // ============================================================
    var logEntries = [];

    function earlyLog(message, level) {
        level = level || 'info';
        var timestamp = new Date().toISOString().substr(11, 12);
        var entry = '[' + timestamp + '] [' + level.toUpperCase() + '] ' + message;
        logEntries.push(entry);
        if (logEntries.length > config.debug.maxLogEntries) {
            logEntries.shift();
        }
        if (config.debug.enabled) {
            try {
                console.log('[InjectPlayer] ' + entry);
            } catch (e) {}
        }
    }

    function adBlockLog(message) {
        earlyLog('[AdBlock] ' + message, 'info');
    }

    // ============================================================
    // 消息提示系统
    // ============================================================
    var messageContainer = null;
    var messageTimeout = null;

    function ensureMessageContainer() {
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.id = 'inject-player-messages';
            messageContainer.style.cssText = 'position:fixed;top:10px;right:10px;z-index:999999;' +
                'max-width:320px;max-height:200px;overflow-y:auto;' +
                'font-size:12px;font-family:monospace;padding:8px;' +
                'background:rgba(30,30,30,0.95);color:#e0e0e0;' +
                'border-radius:8px;border:1px solid #444;' +
                'pointer-events:none;opacity:0.9;';
            document.body.appendChild(messageContainer);
        }
        return messageContainer;
    }

    function showMessage(text, className) {
        try {
            var container = ensureMessageContainer();
            var msg = document.createElement('div');
            msg.className = className || '';
            msg.textContent = text;
            msg.style.cssText = 'margin:2px 0;padding:2px 4px;border-radius:4px;';
            if (className === 'success-message') {
                msg.style.color = '#4caf50';
            } else if (className === 'warn') {
                msg.style.color = '#ff9800';
            } else if (className === 'error') {
                msg.style.color = '#f44336';
            }
            container.appendChild(msg);
            // 限制消息数量
            while (container.childNodes.length > 30) {
                container.removeChild(container.firstChild);
            }
            // 自动隐藏
            if (messageTimeout) {
                clearTimeout(messageTimeout);
            }
            messageTimeout = setTimeout(function() {
                if (container.parentNode) {
                    container.parentNode.removeChild(container);
                    messageContainer = null;
                }
            }, 8000);
        } catch (e) {}
    }

    // ============================================================
    // URL 工具函数
    // ============================================================

    // 检测是否为 m3u8 URL
    function isM3u8Url(url) {
        if (!url) return false;
        var lower = url.toLowerCase();
        return lower.indexOf('.m3u8') > -1 || lower.indexOf('m3u8') > -1 ||
               lower.indexOf('format=m3u8') > -1 || lower.indexOf('type=m3u8') > -1;
    }

    // 优化9: 白名单 URL 检测增强 - 增加路径分析
    function isVideoUrl(url) {
        if (!url) return false;
        var lowerUrl = url.toLowerCase();

        // 1. 白名单关键词在路径中检查（不含查询参数）
        try {
            var urlObj = new URL(url, window.location.href);
            var pathWithFilename = urlObj.pathname;
            var isVideoPath = config.adBlocker.videoWhitelist.some(function(keyword) {
                return pathWithFilename.toLowerCase().indexOf(keyword.toLowerCase()) > -1;
            });
            if (isVideoPath) return true;
        } catch (e) {}

        // 2. 回退到原始逻辑
        return config.adBlocker.videoWhitelist.some(function(keyword) {
            return lowerUrl.indexOf(keyword.toLowerCase()) > -1;
        });
    }

    // 检测是否为广告 URL
    function isAdUrl(url) {
        if (!url) return false;
        var lowerUrl = url.toLowerCase();
        // 先检查是否为视频URL，视频URL不被拦截
        if (isVideoUrl(url)) return false;
        return config.adBlocker.adKeywords.some(function(keyword) {
            return lowerUrl.indexOf(keyword) > -1;
        });
    }

    // ============================================================
    // 优化10: XHR/Fetch 拦截获取视频 URL
    // ============================================================
    var interceptedVideoUrls = [];

    function interceptXHR() {
        try {
            var origXHROpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url) {
                this._injectUrl = url;
                return origXHROpen.apply(this, arguments);
            };

            var origXHRSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.send = function() {
                var self = this;
                self.addEventListener('load', function() {
                    var url = self._injectUrl || self.responseURL || '';
                    if (isM3u8Url(url)) {
                        interceptedVideoUrls.push(url);
                        showMessage('XHR拦截到视频地址: ' + url, 'success-message');
                        earlyLog('XHR拦截到m3u8地址: ' + url, 'info');
                    }
                });
                return origXHRSend.apply(this, arguments);
            };
            earlyLog('XHR拦截已安装', 'info');
        } catch (e) {
            earlyLog('XHR拦截安装失败: ' + e.message, 'warn');
        }
    }

    function interceptFetch() {
        try {
            if (!window.fetch) return;
            var origFetch = window.fetch;
            window.fetch = function(input, init) {
                var url = '';
                if (typeof input === 'string') {
                    url = input;
                } else if (input && input.url) {
                    url = input.url;
                }
                if (isM3u8Url(url)) {
                    interceptedVideoUrls.push(url);
                    showMessage('Fetch拦截到视频地址: ' + url, 'success-message');
                    earlyLog('Fetch拦截到m3u8地址: ' + url, 'info');
                }
                return origFetch.apply(this, arguments);
            };
            earlyLog('Fetch拦截已安装', 'info');
        } catch (e) {
            earlyLog('Fetch拦截安装失败: ' + e.message, 'warn');
        }
    }

    // ============================================================
    // 视频查找
    // ============================================================

    function findVideos(doc) {
        var videos = [];
        try {
            // 1. 查找 <video> 元素
            var videoElements = doc.querySelectorAll('video');
            for (var i = 0; i < videoElements.length; i++) {
                videos.push(videoElements[i]);
            }

            // 2. 查找 <iframe> 中的视频 - 优化12: 先检查同源再访问
            var iframes = doc.querySelectorAll('iframe');
            for (var j = 0; j < iframes.length; j++) {
                var iframe = iframes[j];
                try {
                    var iframeSrc = iframe.src;
                    if (iframeSrc) {
                        var iframeOrigin = new URL(iframeSrc, window.location.href).origin;
                        if (iframeOrigin === window.location.origin) {
                            var iframeDoc = iframe.contentDocument;
                            if (iframeDoc) {
                                var iframeVideos = findVideos(iframeDoc);
                                videos = videos.concat(iframeVideos);
                            }
                        }
                    }
                } catch (e) {
                    // 跨域或无效 URL，跳过
                }
            }

            // 3. 查找 <source> 元素
            var sourceElements = doc.querySelectorAll('source');
            for (var k = 0; k < sourceElements.length; k++) {
                var src = sourceElements[k].src || sourceElements[k].getAttribute('src');
                if (src && isVideoUrl(src)) {
                    earlyLog('找到source视频: ' + src, 'info');
                }
            }
        } catch (e) {
            earlyLog('查找视频失败: ' + e.message, 'warn');
        }
        return videos;
    }

    // ============================================================
    // 优化4: 播放器检测 - 数据驱动框架
    // ============================================================
    var PLAYER_DEFS = [
        {
            type: 'Video.js',
            globalVar: 'videojs',
            globalArray: function() { return window.videojs ? window.videojs.players : null; },
            selectors: ['.video-js', '[data-setup]'],
            instanceProps: ['player', '_player'],
            hasHLS: true,
            canConfigBuffer: true,
            getHlsInstance: function(inst) {
                var tech = inst.tech && inst.tech();
                return (tech && tech.vhs) || (tech && tech.hls) || inst.hls;
            }
        },
        {
            type: 'DPlayer',
            globalVar: 'DPlayer',
            globalArray: function() { return window.dpInstances; },
            selectors: ['.dplayer', '[class*="dplayer"]'],
            instanceProps: ['dp', '_dp', 'dplayer'],
            hasHLS: true,
            canConfigBuffer: true,
            getHlsInstance: function(inst) {
                return (inst.plugins && inst.plugins.hls) || inst.hls;
            }
        },
        {
            type: 'ArtPlayer',
            globalVar: 'Artplayer',
            globalArray: function() { return window.artInstances; },
            selectors: ['.artplayer-app', '.artplayer', '[class*="artplayer"]'],
            instanceProps: ['art', '__art', '_art'],
            hasHLS: true,
            canConfigBuffer: true,
            getHlsInstance: function(inst) {
                return (inst.plugins && inst.plugins.hls) || inst.hls;
            }
        },
        {
            type: 'XGPlayer',
            globalVar: 'Player',
            globalVarCheck: function() {
                return typeof Player !== 'undefined' && Player && Player.prototype &&
                    (Player.toString().indexOf('xgplayer') > -1 ||
                     (Player.plugins && Player.plugins.hls));
            },
            globalArray: function() { return window.xgPlayerInstances; },
            selectors: ['.xgplayer', '.xgplayer-container', '[class*="xgplayer"]'],
            instanceProps: ['player', '_xgplayer', 'xgplayer'],
            hasHLS: true,
            canConfigBuffer: true,
            getHlsInstance: function(inst) {
                return inst.hls || (inst.plugins && inst.plugins.hls) || inst._hls;
            }
        },
        {
            type: 'EasyPlayer',
            globalVar: 'EasyPlayer',
            globalVarCheck: function() {
                return typeof EasyPlayer !== 'undefined' || typeof EasyPlayerPro !== 'undefined';
            },
            globalArray: function() { return window.easyPlayerInstances; },
            selectors: ['.easyplayer', '.easy-player', '[class*="easyplayer"]', '[class*="easy-player"]'],
            instanceProps: ['player', '_easyPlayer', 'easyPlayer'],
            hasHLS: true,
            canConfigBuffer: true,
            getHlsInstance: function(inst) {
                return inst.hls || inst._hls || inst.hlsPlayer || (inst.plugins && inst.plugins.hls);
            }
        },
        {
            type: 'Plyr',
            globalVar: 'plyr',
            globalArray: function() { return window.plyrInstances; },
            selectors: ['.plyr', '[class*="plyr"]'],
            instanceProps: ['plyr', '_plyr'],
            hasHLS: false,
            canConfigBuffer: false,
            getHlsInstance: function() { return null; }
        }
    ];

    function findPlayerInstance(def) {
        // 1. 从全局数组获取
        var globalArray = def.globalArray();
        if (globalArray) {
            var keys = Object.keys(globalArray);
            if (keys.length > 0) {
                earlyLog(def.type + ': 从全局数组获取实例', 'info');
                return globalArray[keys[0]];
            }
        }

        // 2. 从 DOM 元素获取
        for (var i = 0; i < def.selectors.length; i++) {
            var elements = document.querySelectorAll(def.selectors[i]);
            for (var j = 0; j < elements.length; j++) {
                var el = elements[j];
                for (var k = 0; k < def.instanceProps.length; k++) {
                    if (el[def.instanceProps[k]]) {
                        earlyLog(def.type + ': 从DOM元素属性获取实例 (' + def.instanceProps[k] + ')', 'info');
                        return el[def.instanceProps[k]];
                    }
                }
            }
        }

        return null;
    }

    function detectPlayer() {
        earlyLog('开始检测播放器类型...', 'info');

        var playerInfo = {
            type: 'Native',
            instance: null,
            hasHLS: false,
            canConfigBuffer: false,
            def: null
        };

        for (var i = 0; i < PLAYER_DEFS.length; i++) {
            var def = PLAYER_DEFS[i];
            var globalExists = false;

            if (def.globalVarCheck) {
                globalExists = def.globalVarCheck();
            } else {
                globalExists = typeof window[def.globalVar] !== 'undefined';
            }

            if (!globalExists) continue;

            earlyLog('检测到 ' + def.type + ' 全局变量', 'info');
            playerInfo.type = def.type;
            playerInfo.hasHLS = def.hasHLS;
            playerInfo.canConfigBuffer = def.canConfigBuffer;
            playerInfo.def = def;

            // 尝试获取实例
            var instance = findPlayerInstance(def);
            if (instance) {
                playerInfo.instance = instance;
                earlyLog(def.type + ' 实例已获取', 'success');
            } else {
                earlyLog(def.type + ' 实例未找到', 'warn');
            }

            var msg = '检测到 ' + def.type + ' 播放器' + (instance ? '，实例已获取' : '，实例未找到');
            showMessage(msg, 'success-message');
            return playerInfo;
        }

        // 兜底: 通过 DOM 元素检测
        var videoElements = document.querySelectorAll('video');
        if (videoElements.length > 0) {
            earlyLog('未检测到已知播放器框架，发现原生video元素', 'info');
            showMessage('使用原生HTML5视频播放器', 'success-message');
        }

        earlyLog('未检测到任何已知播放器，使用原生播放器', 'warn');
        return playerInfo;
    }

    // ============================================================
    // 优化3: 缓冲优化 - destroy+recreate
    // ============================================================
    var dynamicHlsInstance = null;

    function buildHlsConfig() {
        return {
            maxBufferLength: config.buffer.maxBufferLength,
            maxMaxBufferLength: config.buffer.maxMaxBufferLength,
            maxBufferSize: config.buffer.maxBufferSize,
            backBufferLength: config.buffer.backBufferLength,
            maxBufferHole: config.buffer.maxBufferHole,
            startFragPrefetch: config.buffer.startFragPrefetch,
            capLevelToPlayerSize: config.buffer.capLevelToPlayerSize,
            enableWorker: true,
            enableSoftwareAES: true,
            nudgeOffset: 0.1,
            nudgeMaxRetry: 3,
            maxFragLookUpTolerance: 0.25,
            enableWebVtt: true,
            enableCEA708Captions: true,
            stretchShortVideoTrack: true,
            maxAudioFramesDrift: 1,
            forceKeyFrameOnDiscontinuity: true,
            maxMaxBufferHole: 1,
            fragLoadingTimeOut: 20000,
            fragLoadingMaxRetry: 6,
            fragLoadingMaxRetryTimeout: 64000,
            fragLoadingRetryDelay: 1000,
            levelLoadingTimeOut: 10000,
            levelLoadingMaxRetry: 4,
            levelLoadingRetryDelay: 1000,
            manifestLoadingTimeOut: 10000,
            manifestLoadingMaxRetry: 3,
            manifestLoadingRetryDelay: 1000,
            startLevel: -1,
            highLatencyMode: false,
            liveSyncDuration: 30,
            liveMaxLatencyDuration: Infinity,
            abr: {
                maxBitrate: Infinity,
                minBitrate: 0,
                defaultBitrate: 2000000,
                bandwidthUpgradeTarget: 0.6,
                bandwidthDowngradeTarget: 0.3,
                bandwidthDowngradeDelay: 5,
                bandwidthUpgradeDelay: 3,
                maxStarvationDelay: 2,
                maxLoadingDelay: 2,
                lowLatencyMode: false
            }
        };
    }

    function addHlsEventListeners(hlsInstance, label) {
        if (!hlsInstance || !window.Hls) return;
        label = label || 'HLS';

        try {
            hlsInstance.on(window.Hls.Events.MANIFEST_PARSED, function(event, data) {
                earlyLog(label + ': 播放列表解析完成，共' + data.levels.length + '个质量级别', 'info');
            });

            hlsInstance.on(window.Hls.Events.ERROR, function(event, data) {
                if (data.fatal) {
                    switch (data.type) {
                        case window.Hls.ErrorTypes.NETWORK_ERROR:
                            earlyLog(label + ': 网络错误，正在重试...', 'error');
                            hlsInstance.startLoad();
                            break;
                        case window.Hls.ErrorTypes.MEDIA_ERROR:
                            earlyLog(label + ': 媒体错误，正在恢复...', 'error');
                            hlsInstance.recoverMediaError();
                            break;
                        default:
                            earlyLog(label + ': 致命错误: ' + data.type, 'error');
                            hlsInstance.destroy();
                            break;
                    }
                } else {
                    earlyLog(label + ': 非致命错误: ' + data.type + ' - ' + data.details, 'warn');
                }
            });

            hlsInstance.on(window.Hls.Events.FRAG_BUFFERED, function(event, data) {
                if (data.frag && data.frag.sn % 10 === 0) {
                    earlyLog(label + ': 片段 ' + data.frag.sn + ' 缓冲完成', 'info');
                }
            });
        } catch (e) {
            earlyLog('添加HLS事件监听失败: ' + e.message, 'warn');
        }
    }

    function rebuildHlsInstance(videoElement, oldHls, hlsConfig) {
        try {
            var currentSrc = oldHls.url || videoElement.currentSrc || '';
            var currentTime = videoElement.currentTime || 0;

            earlyLog('重建HLS实例: 当前源=' + currentSrc + ', 位置=' + currentTime, 'info');

            // 1. 销毁旧实例
            oldHls.destroy();

            // 2. 用新配置创建实例
            var newHls = new window.Hls(hlsConfig);
            newHls.attachMedia(videoElement);
            newHls.loadSource(currentSrc);

            // 3. 恢复播放位置
            newHls.on(window.Hls.Events.MANIFEST_PARSED, function() {
                if (currentTime > 0) {
                    videoElement.currentTime = currentTime;
                }
                videoElement.play().catch(function() {});
            });

            // 4. 添加事件监听
            addHlsEventListeners(newHls, 'Rebuilt');

            showMessage('HLS实例已重建，缓冲配置已生效', 'success-message');
            return newHls;
        } catch (e) {
            earlyLog('重建HLS实例失败: ' + e.message, 'error');
            showMessage('HLS重建失败，回退到仅修改config', 'warn');
            return null;
        }
    }

    // 优化播放器缓冲配置
    function optimizePlayerBuffer(playerInfo) {
        if (!playerInfo.canConfigBuffer || !playerInfo.instance) {
            earlyLog('当前播放器不支持缓冲配置优化', 'info');
            return;
        }

        var def = playerInfo.def;
        if (!def) return;

        try {
            var hlsInst = def.getHlsInstance(playerInfo.instance);
            if (hlsInst) {
                dynamicHlsInstance = hlsInst;
                earlyLog('找到HLS实例，准备重建以应用缓冲优化', 'info');

                var videoElement = null;
                // 尝试获取关联的video元素
                if (playerInfo.instance.el && typeof playerInfo.instance.el === 'function') {
                    videoElement = playerInfo.instance.el();
                } else if (playerInfo.instance.el) {
                    videoElement = playerInfo.instance.el;
                } else if (playerInfo.instance.video) {
                    videoElement = playerInfo.instance.video;
                } else {
                    // 从页面查找
                    var vids = document.querySelectorAll('video');
                    if (vids.length > 0) {
                        videoElement = vids[0];
                    }
                }

                if (videoElement && window.Hls) {
                    var newHls = rebuildHlsInstance(videoElement, hlsInst, buildHlsConfig());
                    if (newHls) {
                        dynamicHlsInstance = newHls;
                        // 更新播放器实例中的HLS引用
                        try {
                            if (playerInfo.instance.hls !== undefined) {
                                playerInfo.instance.hls = newHls;
                            }
                            if (playerInfo.instance.plugins && playerInfo.instance.plugins.hls) {
                                playerInfo.instance.plugins.hls = newHls;
                            }
                        } catch (refErr) {
                            earlyLog('更新播放器HLS引用失败: ' + refErr.message, 'warn');
                        }
                        return;
                    }
                }

                // 回退: 仅修改 config 并提示用户刷新
                earlyLog('回退: 仅修改HLS config（需刷新页面生效）', 'warn');
                try {
                    hlsInst.config.maxBufferLength = config.buffer.maxBufferLength;
                    hlsInst.config.maxMaxBufferLength = config.buffer.maxMaxBufferLength;
                    hlsInst.config.maxBufferSize = config.buffer.maxBufferSize;
                    hlsInst.config.backBufferLength = config.buffer.backBufferLength;
                    showMessage('缓冲配置已修改，建议刷新页面使配置完全生效', 'warn');
                } catch (cfgErr) {
                    earlyLog('修改HLS config失败: ' + cfgErr.message, 'error');
                }
            } else {
                earlyLog('未找到HLS实例，跳过缓冲优化', 'info');
            }
        } catch (e) {
            earlyLog('缓冲优化失败: ' + e.message, 'error');
        }
    }

    // 优化原生video元素的缓冲
    function optimizeNativeVideoBuffer(videoElement) {
        if (!videoElement) return;

        try {
            // 检查是否已有HLS.js实例
            if (window.Hls && window.Hls.isSupported()) {
                var src = videoElement.currentSrc || videoElement.src || '';
                if (isM3u8Url(src)) {
                    earlyLog('原生video使用m3u8源，尝试用HLS.js替换', 'info');
                    var hlsConfig = buildHlsConfig();
                    var newHls = new window.Hls(hlsConfig);
                    newHls.attachMedia(videoElement);
                    newHls.loadSource(src);
                    addHlsEventListeners(newHls, 'NativeUpgrade');

                    newHls.on(window.Hls.Events.MANIFEST_PARSED, function() {
                        videoElement.play().catch(function() {});
                    });

                    dynamicHlsInstance = newHls;
                    showMessage('已用HLS.js替换原生播放，缓冲优化已生效', 'success-message');
                }
            }
        } catch (e) {
            earlyLog('原生视频缓冲优化失败: ' + e.message, 'warn');
        }
    }

    // ============================================================
    // 优化11: 卡顿检测+自动降级
    // ============================================================
    var stallCount = 0;
    var lastStallTime = 0;

    function setupStallDetection(videoElement) {
        if (!config.stallDetection.enabled || !videoElement) return;

        videoElement.addEventListener('waiting', function() {
            var now = Date.now();
            if (now - lastStallTime > config.stallDetection.windowMs) {
                stallCount = 1;
            } else {
                stallCount++;
            }
            lastStallTime = now;

            if (stallCount >= config.stallDetection.threshold) {
                showMessage('检测到频繁卡顿，尝试降低缓冲质量...', 'warn');
                earlyLog('卡顿检测触发: 连续' + stallCount + '次卡顿', 'warn');
                autoDowngradeQuality(videoElement);
                stallCount = 0;
            }
        });

        earlyLog('卡顿检测已安装', 'info');
    }

    function autoDowngradeQuality(videoElement) {
        try {
            if (dynamicHlsInstance && dynamicHlsInstance.currentLevel > 0) {
                dynamicHlsInstance.currentLevel = Math.max(0, dynamicHlsInstance.currentLevel - 1);
                showMessage('已降低到质量级别 ' + dynamicHlsInstance.currentLevel, 'success-message');
                earlyLog('自动降级到质量级别: ' + dynamicHlsInstance.currentLevel, 'info');
            } else if (dynamicHlsInstance && dynamicHlsInstance.currentLevel === 0) {
                showMessage('已是最低质量级别，无法继续降级', 'warn');
            } else {
                earlyLog('无HLS实例，无法自动降级', 'warn');
            }
        } catch (e) {
            earlyLog('自动降级失败: ' + e.message, 'error');
        }
    }

    // ============================================================
    // 广告拦截
    // ============================================================

    // 拦截广告元素
    function blockAdElements(root) {
        if (!config.adBlocker.enabled) return;
        root = root || document;

        try {
            // 移除常见广告容器
            var adSelectors = [
                '[class*="ad-container"]', '[class*="ad-wrapper"]',
                '[class*="ad-banner"]', '[class*="ad-slot"]',
                '[id*="ad-container"]', '[id*="ad-wrapper"]',
                '[id*="ad-banner"]', '[id*="google_ads"]',
                '[id*="ad-slot"]', 'ins.adsbygoogle',
                '.ad-placement', '.ad-mark',
                '[class*="preroll"]', '[class*="midroll"]',
                '[class*="postroll"]', '[class*="vast"]'
            ];

            for (var i = 0; i < adSelectors.length; i++) {
                var adElements = root.querySelectorAll(adSelectors[i]);
                for (var j = 0; j < adElements.length; j++) {
                    var el = adElements[j];
                    // 确保不是视频元素
                    if (el.tagName !== 'VIDEO' && el.tagName !== 'SOURCE') {
                        el.parentNode && el.parentNode.removeChild(el);
                        adBlockLog('移除广告元素: ' + adSelectors[i]);
                    }
                }
            }
        } catch (e) {
            earlyLog('广告元素拦截失败: ' + e.message, 'warn');
        }
    }

    // 优化1: 事件拦截替代 defineProperty(window.location, 'href')
    function setupNavigationInterception() {
        // 拦截 beforeunload 事件
        window.addEventListener('beforeunload', function(e) {
            earlyLog('检测到页面导航: ' + (e.target.baseURI || ''), 'info');
        });

        // 拦截 <a> 标签点击
        document.addEventListener('click', function(e) {
            var target = e.target;
            // 向上查找 <a> 标签
            while (target && target.tagName !== 'A') {
                target = target.parentNode;
            }
            if (target && target.href) {
                if (isAdUrl(target.href)) {
                    e.preventDefault();
                    e.stopPropagation();
                    adBlockLog('拦截广告链接: ' + target.href);
                    return false;
                }
            }
        }, true);

        // 拦截 window.open
        var origWindowOpen = window.open;
        window.open = function(url) {
            if (url && isAdUrl(url)) {
                adBlockLog('拦截广告弹窗: ' + url);
                return null;
            }
            return origWindowOpen.apply(this, arguments);
        };

        // 拦截 meta refresh
        var metaTags = document.querySelectorAll('meta[http-equiv="refresh"]');
        for (var i = 0; i < metaTags.length; i++) {
            var content = metaTags[i].content || '';
            var urlMatch = content.match(/url\s*=\s*(.+)/i);
            if (urlMatch && urlMatch[1] && isAdUrl(urlMatch[1])) {
                metaTags[i].parentNode.removeChild(metaTags[i]);
                adBlockLog('移除广告meta刷新: ' + urlMatch[1]);
            }
        }

        earlyLog('导航拦截已安装（事件拦截模式）', 'info');
    }

    // 拦截脚本中的广告请求
    function setupScriptInterception() {
        if (!config.adBlocker.enabled) return;

        try {
            // 拦截动态创建的 script/img 元素
            var origCreateElement = document.createElement;
            document.createElement = function(tagName) {
                var element = origCreateElement.apply(document, arguments);
                var lowerTag = (tagName || '').toLowerCase();

                if (lowerTag === 'script' || lowerTag === 'img' || lowerTag === 'iframe') {
                    var origSetAttribute = element.setAttribute;
                    element.setAttribute = function(name, value) {
                        if ((name === 'src' || name === 'href') && typeof value === 'string' && isAdUrl(value)) {
                            adBlockLog('拦截动态元素广告请求: ' + value);
                            return;
                        }
                        return origSetAttribute.apply(this, arguments);
                    };

                    // 拦截 src 属性直接赋值
                    var origSrcDescriptor = Object.getOwnPropertyDescriptor(
                        lowerTag === 'img' ? HTMLImageElement.prototype :
                        lowerTag === 'iframe' ? HTMLIFrameElement.prototype :
                        HTMLScriptElement.prototype,
                        'src'
                    );
                    if (origSrcDescriptor && origSrcDescriptor.set) {
                        var origSrcSetter = origSrcDescriptor.set;
                        Object.defineProperty(element, 'src', {
                            set: function(value) {
                                if (typeof value === 'string' && isAdUrl(value)) {
                                    adBlockLog('拦截src赋值广告请求: ' + value);
                                    return;
                                }
                                return origSrcSetter.call(this, value);
                            },
                            get: origSrcDescriptor.get,
                            configurable: true
                        });
                    }
                }

                return element;
            };
            earlyLog('脚本拦截已安装', 'info');
        } catch (e) {
            earlyLog('脚本拦截安装失败: ' + e.message, 'warn');
        }
    }

    // ============================================================
    // 净化模式
    // ============================================================
    function applyCleanMode() {
        if (!config.cleanMode.enabled) return;

        try {
            // 移除评论区
            var commentSelectors = [
                '[class*="comment"]', '[id*="comment"]',
                '[class*="discuss"]', '[id*="discuss"]'
            ];
            for (var i = 0; i < commentSelectors.length; i++) {
                var els = document.querySelectorAll(commentSelectors[i]);
                for (var j = 0; j < els.length; j++) {
                    if (els[j].tagName !== 'VIDEO' && els[j].tagName !== 'SOURCE') {
                        els[j].style.display = 'none';
                    }
                }
            }

            // 移除社交分享组件
            if (config.cleanMode.removeSocialWidgets) {
                var socialSelectors = [
                    '[class*="share"]', '[class*="social"]',
                    '[class*="facebook"]', '[class*="twitter"]',
                    '[class*="weibo"]', '[class*="wechat"]'
                ];
                for (var k = 0; k < socialSelectors.length; k++) {
                    var socialEls = document.querySelectorAll(socialSelectors[k]);
                    for (var m = 0; m < socialEls.length; m++) {
                        socialEls[m].style.display = 'none';
                    }
                }
            }

            // 移除推荐视频
            if (config.cleanMode.removeRelatedVideos) {
                var relatedSelectors = [
                    '[class*="related"]', '[class*="recommend"]',
                    '[class*="similar"]', '[class*="suggest"]'
                ];
                for (var n = 0; n < relatedSelectors.length; n++) {
                    var relatedEls = document.querySelectorAll(relatedSelectors[n]);
                    for (var p = 0; p < relatedEls.length; p++) {
                        if (relatedEls[p].tagName !== 'VIDEO') {
                            relatedEls[p].style.display = 'none';
                        }
                    }
                }
            }

            earlyLog('净化模式已应用', 'info');
        } catch (e) {
            earlyLog('净化模式应用失败: ' + e.message, 'warn');
        }
    }

    // ============================================================
    // 全局控制栏
    // ============================================================
    var controlBar = null;
    var controlBarInjected = false;

    function createControlBar(videoElement) {
        if (controlBarInjected) return;
        controlBarInjected = true;

        try {
            controlBar = document.createElement('div');
            controlBar.className = 'video-controls-bar';
            controlBar.style.cssText =
                'position:fixed;bottom:0;left:0;right:0;z-index:999998;' +
                'display:flex;justify-content:center;align-items:center;' +
                'gap:4px;padding:8px 12px;flex-wrap:nowrap;overflow-x:auto;' +
                'background:rgba(45,45,45,0.95);' +
                'border-top:1px solid rgba(60,60,60,0.5);' +
                'font-size:12px;color:#e0e0e0;font-family:sans-serif;';

            // 优化8: backdrop-filter 兼容降级
            // 默认实色背景，@supports 检测后启用 blur
            // (CSS @supports 无法在 JS 内联样式中使用，此处用 JS 检测)
            if (window.getComputedStyle && document.documentElement.style.backdropFilter !== undefined) {
                controlBar.style.background = 'rgba(45,45,45,0.8)';
                controlBar.style.backdropFilter = 'blur(8px)';
                controlBar.style.webkitBackdropFilter = 'blur(8px)';
            }

            // 按钮样式
            var btnStyle =
                'min-width:40px;padding:4px 8px;font-size:11px;border-radius:6px;' +
                'background:#333;color:#e0e0e0;border:1px solid #444;cursor:pointer;' +
                'white-space:nowrap;flex-shrink:0;';

            // 优化7: CSS transition 精确化
            var btnTransition = 'background-color 0.15s ease, border-color 0.15s ease';

            // 快退按钮
            var skipBack3m = createControlButton('<<<3m', btnStyle, btnTransition, function() {
                skipVideo(videoElement, -180);
            });
            var skipBack1m = createControlButton('<<1m', btnStyle, btnTransition, function() {
                skipVideo(videoElement, -60);
            });
            var skipBack30s = createControlButton('<30s', btnStyle, btnTransition, function() {
                skipVideo(videoElement, -30);
            });

            // 快进按钮
            var skipFwd30s = createControlButton('30s>', btnStyle, btnTransition, function() {
                skipVideo(videoElement, 30);
            });
            var skipFwd1m = createControlButton('1m>>', btnStyle, btnTransition, function() {
                skipVideo(videoElement, 60);
            });
            var skipFwd3m = createControlButton('3m>>>', btnStyle, btnTransition, function() {
                skipVideo(videoElement, 180);
            });

            // 倍速选择器
            var rateSelect = document.createElement('select');
            rateSelect.style.cssText = btnStyle + 'min-width:48px;';
            rateSelect.style.transition = btnTransition;
            var rates = [0.5, 1, 1.5, 2, 3, 5, 10, 15];
            for (var i = 0; i < rates.length; i++) {
                var opt = document.createElement('option');
                opt.value = rates[i];
                opt.textContent = rates[i] + 'x';
                if (rates[i] === 1) opt.selected = true;
                rateSelect.appendChild(opt);
            }
            rateSelect.addEventListener('change', function() {
                videoElement.playbackRate = parseFloat(this.value);
                showMessage('倍速: ' + this.value + 'x', 'success-message');
            });

            // 全屏按钮
            var fullscreenBtn = createControlButton('全屏', btnStyle, btnTransition, function() {
                toggleFullscreen(videoElement);
            });

            // 静音按钮
            var muteBtn = createControlButton('静音', btnStyle, btnTransition, function() {
                videoElement.muted = !videoElement.muted;
                this.textContent = videoElement.muted ? '取消静音' : '静音';
            });

            controlBar.appendChild(skipBack3m);
            controlBar.appendChild(skipBack1m);
            controlBar.appendChild(skipBack30s);
            controlBar.appendChild(skipFwd30s);
            controlBar.appendChild(skipFwd1m);
            controlBar.appendChild(skipFwd3m);
            controlBar.appendChild(rateSelect);
            controlBar.appendChild(fullscreenBtn);
            controlBar.appendChild(muteBtn);

            document.body.appendChild(controlBar);
            earlyLog('全局控制栏已注入', 'info');
        } catch (e) {
            earlyLog('创建控制栏失败: ' + e.message, 'error');
        }
    }

    function createControlButton(text, style, transition, onClick) {
        var btn = document.createElement('button');
        btn.textContent = text;
        btn.className = 'control-btn';
        btn.style.cssText = style;
        btn.style.transition = transition;
        btn.addEventListener('click', onClick);
        return btn;
    }

    function skipVideo(videoElement, seconds) {
        if (!videoElement) return;
        var duration = videoElement.duration || 0;
        var currentTime = videoElement.currentTime || 0;
        var newTime = Math.max(0, Math.min(duration, currentTime + seconds));
        videoElement.currentTime = newTime;

        var action = seconds > 0 ? '快进' : '后退';
        var absSec = Math.abs(seconds);
        var timeText = '';
        if (absSec >= 60) {
            timeText = (absSec / 60) + '分钟';
        } else {
            timeText = absSec + '秒';
        }
        showMessage(action + ' ' + timeText, 'success-message');
    }

    function toggleFullscreen(videoElement) {
        if (!videoElement) return;
        try {
            if (!document.fullscreenElement) {
                if (videoElement.requestFullscreen) {
                    videoElement.requestFullscreen();
                } else if (videoElement.webkitRequestFullscreen) {
                    videoElement.webkitRequestFullscreen();
                }
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }
            }
        } catch (e) {
            earlyLog('全屏切换失败: ' + e.message, 'warn');
        }
    }

    // ============================================================
    // 进度条
    // ============================================================
    var progressBar = null;
    var progressFill = null;
    var bufferFill = null;
    var progressInjected = false;

    function createProgressBar(videoElement) {
        if (progressInjected) return;
        progressInjected = true;

        try {
            progressBar = document.createElement('div');
            progressBar.style.cssText =
                'position:fixed;top:0;left:0;right:0;height:4px;z-index:999999;' +
                'background:rgba(255,255,255,0.2);cursor:pointer;';

            bufferFill = document.createElement('div');
            bufferFill.style.cssText =
                'height:100%;background:rgba(255,255,255,0.4);width:0;' +
                'position:absolute;top:0;left:0;';

            progressFill = document.createElement('div');
            progressFill.style.cssText =
                'height:100%;background:#4a9eff;width:0;' +
                'position:absolute;top:0;left:0;';

            progressBar.appendChild(bufferFill);
            progressBar.appendChild(progressFill);
            document.body.appendChild(progressBar);

            // 点击跳转
            progressBar.addEventListener('click', function(e) {
                var rect = progressBar.getBoundingClientRect();
                var ratio = (e.clientX - rect.left) / rect.width;
                if (videoElement.duration) {
                    videoElement.currentTime = ratio * videoElement.duration;
                }
            });

            // 更新进度
            videoElement.addEventListener('timeupdate', function() {
                if (videoElement.duration) {
                    var pct = (videoElement.currentTime / videoElement.duration) * 100;
                    progressFill.style.width = pct + '%';
                }
            });

            videoElement.addEventListener('progress', function() {
                if (videoElement.duration && videoElement.buffered.length > 0) {
                    var bufferedEnd = videoElement.buffered.end(videoElement.buffered.length - 1);
                    var bufPct = (bufferedEnd / videoElement.duration) * 100;
                    bufferFill.style.width = bufPct + '%';
                }
            });

            earlyLog('进度条已注入', 'info');
        } catch (e) {
            earlyLog('创建进度条失败: ' + e.message, 'error');
        }
    }

    // ============================================================
    // 调试信息区域
    // ============================================================
    var debugPanel = null;
    var debugInjected = false;

    function createDebugPanel() {
        if (debugInjected) return;
        debugInjected = true;

        try {
            debugPanel = document.createElement('div');
            debugPanel.style.cssText =
                'position:fixed;bottom:60px;right:10px;z-index:999997;' +
                'max-width:300px;max-height:200px;overflow-y:auto;' +
                'font-size:10px;font-family:monospace;padding:6px;' +
                'background:rgba(0,0,0,0.85);color:#0f0;' +
                'border-radius:6px;border:1px solid #333;' +
                'display:none;word-break:break-all;';

            var toggleBtn = document.createElement('button');
            toggleBtn.textContent = 'Debug';
            toggleBtn.style.cssText =
                'position:fixed;bottom:60px;right:10px;z-index:999998;' +
                'padding:4px 8px;font-size:10px;border-radius:4px;' +
                'background:#333;color:#0f0;border:1px solid #555;cursor:pointer;';
            toggleBtn.addEventListener('click', function() {
                if (debugPanel.style.display === 'none') {
                    debugPanel.style.display = 'block';
                    updateDebugInfo();
                } else {
                    debugPanel.style.display = 'none';
                }
            });

            document.body.appendChild(debugPanel);
            document.body.appendChild(toggleBtn);
            earlyLog('调试面板已注入', 'info');
        } catch (e) {
            earlyLog('创建调试面板失败: ' + e.message, 'warn');
        }
    }

    function updateDebugInfo() {
        if (!debugPanel) return;
        try {
            var videos = document.querySelectorAll('video');
            var info = '=== 调试信息 ===\n';
            info += '视频元素数: ' + videos.length + '\n';
            info += '拦截视频URL: ' + interceptedVideoUrls.length + '\n';

            if (videos.length > 0) {
                var v = videos[0];
                info += '当前源: ' + (v.currentSrc || v.src || '无') + '\n';
                info += '播放状态: ' + (v.paused ? '暂停' : '播放中') + '\n';
                info += '当前时间: ' + v.currentTime.toFixed(1) + 's\n';
                info += '总时长: ' + (v.duration ? v.duration.toFixed(1) : '未知') + 's\n';
                info += '缓冲: ' + (v.buffered.length > 0 ? v.buffered.end(v.buffered.length - 1).toFixed(1) + 's' : '无') + '\n';
                info += '倍速: ' + v.playbackRate + 'x\n';
                info += '音量: ' + Math.round(v.volume * 100) + '%\n';
            }

            if (dynamicHlsInstance) {
                info += 'HLS级别: ' + dynamicHlsInstance.currentLevel + '\n';
                info += 'HLS自动级别: ' + dynamicHlsInstance.autoLevelEnabled + '\n';
            }

            info += '\n=== 最近日志 ===\n';
            var recentLogs = logEntries.slice(-20);
            for (var i = 0; i < recentLogs.length; i++) {
                info += recentLogs[i] + '\n';
            }

            debugPanel.textContent = info;
        } catch (e) {}
    }

    // ============================================================
    // 版权信息
    // ============================================================
    function injectCopyright() {
        try {
            var copyright = document.createElement('div');
            copyright.style.cssText =
                'position:fixed;bottom:50px;left:10px;z-index:999997;' +
                'font-size:9px;color:#666;font-family:monospace;' +
                'pointer-events:none;opacity:0.7;';
            copyright.textContent = 'InjectPlayer V3.20260606.1 | Miss光头强';
            document.body.appendChild(copyright);
        } catch (e) {}
    }

    // ============================================================
    // 自动播放+静音
    // ============================================================
    function autoPlayVideo(videoElement) {
        if (!config.autoPlay.enabled || !videoElement) return;

        var retryCount = 0;

        function tryAutoPlay() {
            if (retryCount >= config.autoPlay.retryCount) {
                earlyLog('自动播放重试次数已用尽', 'warn');
                return;
            }

            videoElement.muted = config.autoPlay.muted;
            var playPromise = videoElement.play();

            if (playPromise && typeof playPromise.then === 'function') {
                playPromise.then(function() {
                    earlyLog('自动播放成功', 'info');
                    showMessage('自动播放已启动', 'success-message');
                }).catch(function(err) {
                    retryCount++;
                    earlyLog('自动播放失败(第' + retryCount + '次): ' + err.message, 'warn');
                    setTimeout(tryAutoPlay, config.autoPlay.retryDelay);
                });
            } else {
                earlyLog('自动播放已触发（无Promise）', 'info');
            }
        }

        tryAutoPlay();
    }

    // ============================================================
    // 优化5+6+13: MutationObserver（限制范围+移除定时器+meta refresh）
    // ============================================================
    function setupMutationObserver() {
        try {
            var observer = new MutationObserver(function(mutations) {
                for (var i = 0; i < mutations.length; i++) {
                    var mutation = mutations[i];
                    for (var j = 0; j < mutation.addedNodes.length; j++) {
                        var node = mutation.addedNodes[j];

                        // 优化13: 动态 meta refresh 处理
                        if (node.tagName === 'META' && node.httpEquiv === 'refresh') {
                            if (!isVideoUrl(node.content || '')) {
                                node.parentNode.removeChild(node);
                                adBlockLog('移除动态插入的广告meta刷新');
                            }
                        }

                        // 广告元素拦截
                        if (node.nodeType === 1) {
                            blockAdElements(node.parentNode || document);
                        }
                    }
                }
            });

            // 优化5: 只监听 body 的直接子元素变化，不监听子树
            observer.observe(document.body, {
                childList: true,
                subtree: false
            });

            earlyLog('MutationObserver已安装（subtree:false）', 'info');
        } catch (e) {
            earlyLog('MutationObserver安装失败: ' + e.message, 'warn');
        }
    }

    // 注意: 优化6 - 已移除 setInterval(blockAdElements, 10000)
    // 仅依赖 MutationObserver 的增量触发

    // ============================================================
    // 注入全局 CSS 样式
    // ============================================================
    function injectGlobalStyles() {
        try {
            var style = document.createElement('style');
            style.textContent =
                // 优化7: CSS transition 精确化
                '.control-btn { transition: background-color 0.15s ease, border-color 0.15s ease; }\n' +
                '.control-btn:hover { background-color: #3d3d3d !important; border-color: #555 !important; }\n' +
                '.control-btn:active { background-color: #444 !important; transform: scale(0.98); }\n' +
                // 优化8: backdrop-filter 兼容降级
                '.video-controls-bar { background: rgba(45, 45, 45, 0.95); }\n' +
                '@supports (backdrop-filter: blur(1px)) {\n' +
                '  .video-controls-bar { background: rgba(45, 45, 45, 0.8); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }\n' +
                '}\n' +
                // 视频元素优化
                'video { max-width: 100% !important; background: #000 !important; }\n' +
                // 隐藏常见广告
                '[class*="ad-container"], [class*="ad-wrapper"], [class*="ad-banner"], ' +
                '[id*="google_ads"], ins.adsbygoogle { display: none !important; }\n';
            document.head.appendChild(style);
            earlyLog('全局样式已注入', 'info');
        } catch (e) {
            earlyLog('全局样式注入失败: ' + e.message, 'warn');
        }
    }

    // ============================================================
    // 主初始化流程
    // ============================================================
    function init() {
        earlyLog('=== InjectPlayer V3.20260606.1 初始化 ===', 'info');

        // 1. 安装 XHR/Fetch 拦截
        interceptXHR();
        interceptFetch();

        // 2. 安装导航拦截（事件拦截模式，替代 defineProperty）
        setupNavigationInterception();

        // 3. 安装脚本拦截
        setupScriptInterception();

        // 4. 注入全局样式
        injectGlobalStyles();

        // 5. 检测播放器
        var playerInfo = detectPlayer();

        // 6. 查找视频元素
        var videos = findVideos(document);
        var videoElement = videos.length > 0 ? videos[0] : null;

        if (!videoElement) {
            earlyLog('未找到视频元素，等待动态加载...', 'warn');
            // 等待视频元素出现
            waitForVideoElement();
            return;
        }

        earlyLog('找到视频元素: ' + videos.length + '个', 'info');

        // 7. 优化缓冲配置
        if (playerInfo.type !== 'Native' && playerInfo.instance) {
            optimizePlayerBuffer(playerInfo);
        } else if (videoElement) {
            optimizeNativeVideoBuffer(videoElement);
        }

        // 8. 安装卡顿检测
        setupStallDetection(videoElement);

        // 9. 创建控制栏
        createControlBar(videoElement);

        // 10. 创建进度条
        createProgressBar(videoElement);

        // 11. 创建调试面板
        createDebugPanel();

        // 12. 注入版权信息
        injectCopyright();

        // 13. 应用净化模式
        applyCleanMode();

        // 14. 拦截广告元素
        blockAdElements();

        // 15. 自动播放
        autoPlayVideo(videoElement);

        // 16. 安装 MutationObserver
        setupMutationObserver();

        // 17. 定期更新调试信息
        setInterval(function() {
            if (debugPanel && debugPanel.style.display !== 'none') {
                updateDebugInfo();
            }
        }, 3000);

        earlyLog('=== InjectPlayer 初始化完成 ===', 'info');
        showMessage('InjectPlayer V3 已就绪 (' + playerInfo.type + ')', 'success-message');
    }

    // 等待视频元素出现
    function waitForVideoElement() {
        var checkCount = 0;
        var maxChecks = 60; // 最多等待30秒

        var checkInterval = setInterval(function() {
            checkCount++;
            var videos = findVideos(document);

            if (videos.length > 0) {
                clearInterval(checkInterval);
                earlyLog('视频元素已出现，继续初始化', 'info');
                // 重新初始化
                var playerInfo = detectPlayer();
                var videoElement = videos[0];

                if (playerInfo.type !== 'Native' && playerInfo.instance) {
                    optimizePlayerBuffer(playerInfo);
                } else {
                    optimizeNativeVideoBuffer(videoElement);
                }

                setupStallDetection(videoElement);
                createControlBar(videoElement);
                createProgressBar(videoElement);
                createDebugPanel();
                injectCopyright();
                applyCleanMode();
                blockAdElements();
                autoPlayVideo(videoElement);
                setupMutationObserver();

                earlyLog('=== InjectPlayer 延迟初始化完成 ===', 'info');
                showMessage('InjectPlayer V3 已就绪（延迟）', 'success-message');
            } else if (checkCount >= maxChecks) {
                clearInterval(checkInterval);
                earlyLog('等待视频元素超时', 'warn');
                showMessage('未找到视频元素', 'warn');
            }
        }, 500);
    }

    // ============================================================
    // 启动
    // ============================================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
