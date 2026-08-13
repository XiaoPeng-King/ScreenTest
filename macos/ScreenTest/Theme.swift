import SwiftUI

enum Theme {
    static let bg = Color(red: 15 / 255, green: 17 / 255, blue: 21 / 255)
    static let card = Color(red: 26 / 255, green: 29 / 255, blue: 36 / 255)
    static let inner = Color(red: 37 / 255, green: 42 / 255, blue: 52 / 255)
    static let control = Color(red: 45 / 255, green: 51 / 255, blue: 64 / 255)
    static let accent = Color(red: 59 / 255, green: 130 / 255, blue: 246 / 255)
    static let accentDark = Color(red: 37 / 255, green: 99 / 255, blue: 235 / 255)
    static let text = Color(red: 232 / 255, green: 234 / 255, blue: 237 / 255)
    static let muted = Color(red: 154 / 255, green: 160 / 255, blue: 166 / 255)
    static let faint = Color(red: 107 / 255, green: 114 / 255, blue: 128 / 255)
}

enum ExportPreset: Identifiable {
    case named(String, Int, Int)

    var id: String {
        switch self {
        case .named(let name, let w, let h):
            return "\(name)-\(w)x\(h)"
        }
    }

    var title: String {
        switch self {
        case .named(let name, _, _): return name
        }
    }

    var width: Int {
        switch self {
        case .named(_, let w, _): return w
        }
    }

    var height: Int {
        switch self {
        case .named(_, _, let h): return h
        }
    }

    static let standard: [ExportPreset] = [
        .named("1080p", 1920, 1080),
        .named("1440p", 2560, 1440),
        .named("4K", 3840, 2160),
        .named("720p", 1280, 720),
        .named("正方形", 1080, 1080),
    ]
}
