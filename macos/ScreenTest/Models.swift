import AppKit
import CoreGraphics
import SwiftUI

enum AppInfo {
    static let name = "ScreenTest"
    static let title = "ScreenTest - 屏幕测试工具"
    static let version = "1.2.5"
    static let siteURL = URL(string: "https://www.xiaopengking.site")!
    static let siteDisplay = "xiaopengking.site"
}

struct RGBColor: Hashable, Sendable {
    var r: UInt8
    var g: UInt8
    var b: UInt8

    static let black = RGBColor(r: 0, g: 0, b: 0)
    static let white = RGBColor(r: 255, g: 255, b: 255)

    var hex: String { String(format: "#%02X%02X%02X", r, g, b) }

    var nsColor: NSColor {
        NSColor(
            deviceRed: CGFloat(r) / 255.0,
            green: CGFloat(g) / 255.0,
            blue: CGFloat(b) / 255.0,
            alpha: 1
        )
    }

    var color: Color { Color(nsColor: nsColor) }

    var luminance: Double {
        0.299 * Double(r) + 0.587 * Double(g) + 0.114 * Double(b)
    }

    var contrasting: RGBColor { luminance > 140 ? .black : .white }

    var cgColor: CGColor { nsColor.cgColor }
}

struct SolidPreset: Identifiable, Hashable, Sendable {
    var name: String
    var rgb: RGBColor
    var id: String { name }
}

enum SolidPresets {
    static let all: [SolidPreset] = [
        .init(name: "黑色", rgb: .init(r: 0, g: 0, b: 0)),
        .init(name: "白色", rgb: .init(r: 255, g: 255, b: 255)),
        .init(name: "红色", rgb: .init(r: 255, g: 0, b: 0)),
        .init(name: "绿色", rgb: .init(r: 0, g: 255, b: 0)),
        .init(name: "蓝色", rgb: .init(r: 0, g: 0, b: 255)),
        .init(name: "青色", rgb: .init(r: 0, g: 255, b: 255)),
        .init(name: "品红", rgb: .init(r: 255, g: 0, b: 255)),
        .init(name: "黄色", rgb: .init(r: 255, g: 255, b: 0)),
        .init(name: "灰色 50%", rgb: .init(r: 128, g: 128, b: 128)),
        .init(name: "深灰 25%", rgb: .init(r: 64, g: 64, b: 64)),
        .init(name: "浅灰 75%", rgb: .init(r: 192, g: 192, b: 192)),
        .init(name: "橙色", rgb: .init(r: 255, g: 128, b: 0)),
        .init(name: "紫色", rgb: .init(r: 128, g: 0, b: 255)),
        .init(name: "粉色", rgb: .init(r: 255, g: 105, b: 180)),
    ]

    static func name(for rgb: RGBColor) -> String {
        all.first(where: { $0.rgb == rgb })?.name ?? "RGB(\(rgb.r),\(rgb.g),\(rgb.b))"
    }
}

enum GrayLevels {
    static let all: [UInt8] = [0, 16, 32, 48, 64, 96, 128, 160, 192, 224, 240, 255]
}

enum PatternKind: String, CaseIterable, Identifiable, Sendable {
    case checker
    case grid
    case hline
    case vline
    case crosshatch
    case colorbars
    case gradientH
    case gradientV
    case gradientGray
    case dots
    case textFocus

    var id: String { rawValue }

    var title: String {
        switch self {
        case .checker: return "棋盘格"
        case .grid: return "网格"
        case .hline: return "水平细线"
        case .vline: return "垂直细线"
        case .crosshatch: return "交叉线"
        case .colorbars: return "彩条"
        case .gradientH: return "水平渐变"
        case .gradientV: return "垂直渐变"
        case .gradientGray: return "灰度渐变"
        case .dots: return "点阵"
        case .textFocus: return "文字锐度"
        }
    }

    var subtitle: String {
        switch self {
        case .checker: return "几何与清晰度"
        case .grid: return "对齐与畸变"
        case .hline: return "水平解析力"
        case .vline: return "垂直解析力"
        case .crosshatch: return "综合几何"
        case .colorbars: return "色彩还原"
        case .gradientH: return "色带检测"
        case .gradientV: return "垂直色阶"
        case .gradientGray: return "伽马/色带"
        case .dots: return "像素均匀性"
        case .textFocus: return "清晰度"
        }
    }

    var overlayLabel: String {
        switch self {
        case .checker: return "棋盘格 (几何/清晰度)"
        case .grid: return "网格 (几何/对齐)"
        case .hline: return "水平线 (1px 黑白交替)"
        case .vline: return "垂直线 (1px 黑白交替)"
        case .crosshatch: return "交叉线"
        case .colorbars: return "彩条 (SMPTE 风格)"
        case .gradientH: return "水平 RGB 渐变 (色带/色阶)"
        case .gradientV: return "垂直 RGB 渐变"
        case .gradientGray: return "灰度渐变 (色带/伽马)"
        case .dots: return "点阵"
        case .textFocus: return "文字清晰度 / 锐度测试"
        }
    }
}

enum EffectKind: String, CaseIterable, Identifiable, Sendable {
    case dim
    case bouncing
    case matrix
    case noise

    var id: String { rawValue }

    var title: String {
        switch self {
        case .dim: return "暗屏屏保"
        case .bouncing: return "弹跳 Logo"
        case .matrix: return "矩阵雨"
        case .noise: return "静态雪花"
        }
    }

    var subtitle: String {
        switch self {
        case .dim: return "全黑低干扰，适合休息"
        case .bouncing: return "经典弹跳文字屏保"
        case .matrix: return "绿色数字雨特效"
        case .noise: return "电视雪花噪点效果"
        }
    }
}

enum MainTab: String, CaseIterable, Identifiable {
    case dead = "坏点检测"
    case color = "纯色 / 灰度"
    case pattern = "图案测试"
    case effect = "屏保特效"
    case export = "纯色图片"

    var id: String { rawValue }
}

enum TestMode: Equatable, Sendable {
    case deadPixel
    case solid
    case custom
    case gray
    case pattern
    case effect
}

struct TestConfiguration: Equatable {
    var mode: TestMode
    var colors: [RGBColor]
    var customColor: RGBColor
    var pattern: PatternKind
    var effect: EffectKind
    var autoInterval: TimeInterval
    var grayStart: UInt8?

    static func deadPixel(interval: TimeInterval) -> TestConfiguration {
        TestConfiguration(
            mode: .deadPixel,
            colors: SolidPresets.all.map(\.rgb),
            customColor: .black,
            pattern: .checker,
            effect: .dim,
            autoInterval: interval
        )
    }
}

struct MonitorInfo: Identifiable, Hashable {
    let id: CGDirectDisplayID
    let index: Int
    let frame: CGRect
    let pixelWidth: Int
    let pixelHeight: Int
    let scale: CGFloat
    let primary: Bool
    let name: String
    let refreshHz: Int

    var scalePercent: Int { Int((scale * 100).rounded()) }

    var label: String {
        let tag = primary ? "主屏" : "外接"
        let scaleText = abs(scale - 1) > 0.01 ? " · 缩放\(scalePercent)%" : ""
        let hz = refreshHz > 0 ? " · \(refreshHz)Hz" : ""
        let namePart = name.isEmpty ? "" : " · \(name)"
        return "显示器 \(index + 1)（\(tag)）\(pixelWidth)×\(pixelHeight)\(hz)\(scaleText)\(namePart)"
    }

    var nsScreen: NSScreen? {
        MonitorService.screen(forID: id) ?? MonitorService.screen(for: self)
    }
}
