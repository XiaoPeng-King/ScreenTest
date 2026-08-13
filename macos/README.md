# ScreenTest for macOS

本目录是 [ScreenTest](https://github.com/XiaoPeng-King/ScreenTest) 的 macOS 原生版，与仓库根目录的 Windows 桌面版功能对齐：坏点检测、纯色/灰度、几何图案、屏保特效、纯色图片导出，以及多显示器选择（含外接屏）。

> 个人网站：[xiaopengking.site](https://www.xiaopengking.site)

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%2014%2B-lightgrey.svg)
![Swift](https://img.shields.io/badge/Swift-5-orange.svg)

## 相对 Windows 版的差异

| 点 | 说明 |
|----|------|
| 原生 App | SwiftUI + AppKit，双击 `ScreenTest.app` 即可运行，无需 Python |
| 真像素绘制 | 细线 / 棋盘 / 渐变按显示器 `backingScaleFactor` 以物理像素生成，Retina 上仍是 1px |
| 多显示器 | 用 `NSScreen` 枚举内建屏、外接屏、Sidecar；全屏窗口铺满目标屏（含菜单栏与刘海区域） |
| 跨屏操作 | 在副屏打开控制窗口，可指定主屏测试，副屏控制窗口保持可见 |
| 颜色 | 使用 **device RGB**，坏点测试输出纯 (255,0,0) 等面板值 |
| 字体 | 系统字体 / 苹方 / SF Mono，不再依赖微软雅黑 |

## 功能

| 模块 | 说明 |
|------|------|
| **坏点检测** | 全屏纯色循环（黑/白/RGB/青/品红/黄/灰等），检测坏点、亮点、卡死子像素 |
| **纯色显示** | 自定义 RGB + 系统取色器，一键全屏 |
| **灰度测试** | 0–255 多级灰度快捷切换与循环 |
| **图案测试** | 棋盘格、网格、1px 细线、彩条、RGB/灰度渐变、点阵、文字锐度 |
| **屏保特效** | 暗屏、弹跳 Logo、矩阵雨、静态雪花 |
| **纯色图片** | 自定义分辨率与颜色，导出 PNG/JPEG |
| **多显示器** | 枚举主屏/外接屏真实分辨率，指定目标屏全屏测试 |

## 系统要求

- macOS 14 Sonoma 或更高
- Apple Silicon 或 Intel
- 无需安装 Python / Homebrew 依赖（打包图标时 `build.sh` 会用到系统自带的 `python3` / `sips`）

## 运行

```bash
cd macos
./build.sh
open dist/ScreenTest.app
```

或用 Xcode 打开 `macos/ScreenTest.xcodeproj`，选择 **ScreenTest** scheme 后 Run。

## 全屏快捷键

| 按键 | 功能 |
|------|------|
| `Esc` / `F11` | 退出全屏测试 |
| `空格` / 左键 | 下一页 |
| `←` / 右键 | 上一页 |
| `A` | 开关自动循环 |

菜单栏也提供「刷新显示器」「识别显示器」。

## 项目结构

```
macos/
├── ScreenTest/                 # 源码
├── ScreenTest.xcodeproj
├── build.sh                    # 一键 Release 打包
├── scripts/make_icon.py
└── README.md
```

## 许可

本项目基于 [MIT License](../LICENSE) 开源，与 Windows 版相同。

## 作者

- GitHub: [@XiaoPeng-King](https://github.com/XiaoPeng-King)
- Website: [xiaopengking.site](https://www.xiaopengking.site)
