# 广播接收器体系

> 项目广播接收器清单与注册机制。接收器分两类：`receiver/` 包内独立类 + Service 内部匿名接收器。

## 概述

广播接收器承担三类职责：系统事件桥接（时间/电量/网络/媒体键 → EventBus）、桌面小部件（Widget Provider）、分享与开机等外部入口。接收器普遍很薄，`onReceive` 内仅做事件转发或启动服务，业务逻辑下沉到 Model 层。

## 核心类清单

| 类名 | 路径 | 职责 |
|------|------|------|
| MediaButtonReceiver | app/src/main/java/io/legado/app/receiver/MediaButtonReceiver.kt | 监听耳机媒体键，按朗读/音频播放状态分发播放/暂停/上一曲/下一曲 |
| TimeBatteryReceiver | app/src/main/java/io/legado/app/receiver/TimeBatteryReceiver.kt | 监听 `ACTION_TIME_TICK` 与 `ACTION_BATTERY_CHANGED`，postEvent `TIME_CHANGED`/`BATTERY_CHANGED` |
| NetworkChangedListener | app/src/main/java/io/legado/app/receiver/NetworkChangedListener.kt | 网络状态变化监听，通知下载/同步等任务网络可用性 |
| ReadGoalWidgetProvider | app/src/main/java/io/legado/app/receiver/ReadGoalWidgetProvider.kt | 阅读目标桌面小部件 Provider（AppWidgetProvider） |
| ReadRankWidgetProvider | app/src/main/java/io/legado/app/receiver/ReadRankWidgetProvider.kt | 阅读排行桌面小部件 Provider（AppWidgetProvider） |
| SharedReceiverActivity | app/src/main/java/io/legado/app/receiver/SharedReceiverActivity.kt | 系统分享入口 Activity（接收文本/URL 转入关联导入链路） |
| RelayBootReceiver | app/src/main/java/io/legado/app/service/relay/RelayBootReceiver.kt | 开机广播，恢复中继相关服务 |

## 关键机制

- **动态注册 + EventBus 桥接**：`TimeBatteryReceiver` 自带 `IntentFilter`（TIME_TICK/BATTERY_CHANGED），由宿主（阅读界面）动态注册/注销，`onReceive` 通过 `postEvent` 转成 EventBus 事件驱动 UI 刷新。
- **媒体键分发**：`MediaButtonReceiver` 依据 `ReadAloud` / `AudioPlay` 当前状态与前台页面（ReadBookActivity/AudioPlayActivity）决定控制目标，键值经 KeyEvent 判断。
- **Widget 静态注册**：两个 Widget Provider 在 AndroidManifest 中声明，点击跳转对应入口页。
- **Service 内部接收器**：`AudioPlayService`、`VideoPlayService`、`BaseReadAloudService` 内含内部 BroadcastReceiver（如音频失效 AudioManager.ACTION_AUDIO_BECOMING_NOISY 处理），随服务生命周期注册注销。
- **深入阅读**：分享/URL 入口与 Deep Link 路由见 [association-import.md](./association-import.md) 与 [intent-deep-links.md](../architecture/intent-deep-links.md)；Service 生命周期见 [android-services.md](./android-services.md)。
