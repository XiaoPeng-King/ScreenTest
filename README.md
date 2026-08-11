# ScreenTest Desktop

本地桌面版屏幕测试工具（Windows），支持坏点检测、纯色/灰度、几何图案、屏保特效与纯色图片导出，并支持多显示器选择（含外接屏）。

> 个人网站：[xiaopengking.site](https://www.xiaopengking.site)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](#)

## 功能

| 模块 | 说明 |
|------|------|
| **坏点检测** | 全屏纯色循环（黑/白/RGB/青/品红/黄/灰等），检测坏点、亮点、卡死子像素 |
| **纯色显示** | 自定义 RGB + 取色器，一键全屏 |
| **灰度测试** | 0–255 多级灰度快捷切换与循环 |
| **图案测试** | 棋盘格、网格、1px 细线、彩条、RGB/灰度渐变、点阵、文字锐度 |
| **屏保特效** | 暗屏、弹跳 Logo、矩阵雨、静态雪花 |
| **纯色图片** | 自定义分辨率与颜色，导出 PNG/JPEG |
| **多显示器** | 枚举主屏/外接屏真实分辨率，指定目标屏全屏测试 |

## 截图说明

运行后顶部可选择「测试目标显示器」，再进入对应标签页开始测试。

## 下载 EXE（推荐）

前往 [Releases](https://github.com/XiaoPeng-King/ScreenTest/releases) 下载 **ScreenTest.exe**，双击即可运行（无需安装 Python）。

当前版本：[v1.2.5](https://github.com/XiaoPeng-King/ScreenTest/releases/tag/v1.2.5)

## 运行（源码）

```bash
# 依赖
pip install -r requirements.txt

# 启动
python screentest.py
```

系统要求：

- Windows 10 / 11
- Python 3.10+
- 依赖：`pillow`

## 打包为 EXE

```bash
pip install -r requirements.txt
build.bat
```

或手动：

```bash
pyinstaller --noconfirm --onefile --windowed --name ScreenTest screentest.py
```

生成文件：`dist/ScreenTest.exe`（可直接分发，目标机器无需安装 Python）。

## 全屏快捷键

| 按键 | 功能 |
|------|------|
| `Esc` / `F11` | 退出全屏测试 |
| `空格` / 左键 | 下一页 |
| `←` / 右键 | 上一页 |
| `A` | 开关自动循环 |

## 项目结构

```
ScreenTest/
├── screentest.py      # 主程序
├── requirements.txt   # 依赖
├── build.bat          # 一键打包脚本
├── LICENSE            # MIT
└── README.md
```

## 许可

本项目基于 [MIT License](LICENSE) 开源。

## 作者

- GitHub: [@XiaoPeng-King](https://github.com/XiaoPeng-King)
- Website: [xiaopengking.site](https://www.xiaopengking.site)
