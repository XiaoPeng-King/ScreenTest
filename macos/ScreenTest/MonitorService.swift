import AppKit
import CoreGraphics

enum MonitorService {
    static func enumerate() -> [MonitorInfo] {
        var raw: [(screen: NSScreen, id: CGDirectDisplayID, primary: Bool)] = []

        for screen in NSScreen.screens {
            guard let id = displayID(for: screen) else { continue }
            raw.append((screen, id, CGDisplayIsMain(id) != 0))
        }

        raw.sort { lhs, rhs in
            if lhs.primary != rhs.primary { return lhs.primary && !rhs.primary }
            if lhs.screen.frame.minX != rhs.screen.frame.minX {
                return lhs.screen.frame.minX < rhs.screen.frame.minX
            }
            return lhs.screen.frame.minY > rhs.screen.frame.minY
        }

        return raw.enumerated().map { index, item in
            let screen = item.screen
            let id = item.id
            let scale = screen.backingScaleFactor
            let frame = screen.frame
            let pixelW = max(1, Int((frame.width * scale).rounded()))
            let pixelH = max(1, Int((frame.height * scale).rounded()))
            return MonitorInfo(
                id: id,
                index: index,
                frame: frame,
                pixelWidth: pixelW,
                pixelHeight: pixelH,
                scale: scale,
                primary: item.primary,
                name: screen.localizedName,
                refreshHz: refreshRate(for: id, screen: screen)
            )
        }
    }

    static func displayID(for screen: NSScreen) -> CGDirectDisplayID? {
        let key = NSDeviceDescriptionKey("NSScreenNumber")
        if let number = screen.deviceDescription[key] as? NSNumber {
            return CGDirectDisplayID(truncating: number)
        }
        return screen.deviceDescription[key] as? CGDirectDisplayID
    }

    static func screen(forID id: CGDirectDisplayID) -> NSScreen? {
        NSScreen.screens.first { displayID(for: $0) == id }
    }

    static func screen(for monitor: MonitorInfo) -> NSScreen? {
        if let match = screen(forID: monitor.id) {
            return match
        }
        if monitor.primary {
            return NSScreen.screens.first(where: { screen in
                displayID(for: screen).map { CGDisplayIsMain($0) != 0 } ?? false
            }) ?? NSScreen.main ?? NSScreen.screens.first
        }
        return NSScreen.screens.first { $0.frame.equalTo(monitor.frame) }
    }

    static func refreshRate(for id: CGDirectDisplayID, screen: NSScreen) -> Int {
        if let mode = CGDisplayCopyDisplayMode(id) {
            let hz = mode.refreshRate
            if hz > 0 { return Int(hz.rounded()) }
        }
        let fps = screen.maximumFramesPerSecond
        return fps > 0 ? fps : 0
    }
}

@MainActor
final class IdentifyOverlayController {
    private var windows: [NSWindow] = []
    private var hideWork: DispatchWorkItem?

    func show(monitors: [MonitorInfo], duration: TimeInterval = 2.5) {
        hide()
        for monitor in monitors {
            guard let screen = monitor.nsScreen else { continue }
            let window = OverlayWindow(
                contentRect: CGRect(origin: .zero, size: screen.frame.size),
                styleMask: .borderless,
                backing: .buffered,
                defer: false,
                screen: screen
            )
            window.setFrame(screen.frame, display: true)
            window.isOpaque = true
            window.backgroundColor = NSColor(deviceRed: 11 / 255, green: 18 / 255, blue: 32 / 255, alpha: 1)
            window.level = NSWindow.Level(rawValue: Int(CGWindowLevelForKey(.statusWindow)))
            window.hasShadow = false
            window.ignoresMouseEvents = true
            window.collectionBehavior = [.canJoinAllSpaces, .transient, .ignoresCycle]
            window.contentView = IdentifyView(monitor: monitor)
            window.orderFrontRegardless()
            window.setFrame(screen.frame, display: true)
            windows.append(window)
        }

        let work = DispatchWorkItem { [weak self] in
            self?.hide()
        }
        hideWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + duration, execute: work)
    }

    func hide() {
        hideWork?.cancel()
        hideWork = nil
        windows.forEach { $0.orderOut(nil) }
        windows.removeAll()
    }
}

private final class IdentifyView: NSView {
    private let monitor: MonitorInfo

    init(monitor: MonitorInfo) {
        self.monitor = monitor
        super.init(frame: .zero)
        wantsLayer = true
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override var isFlipped: Bool { true }

    override func draw(_ dirtyRect: NSRect) {
        NSColor(deviceRed: 11 / 255, green: 18 / 255, blue: 32 / 255, alpha: 1).setFill()
        bounds.fill()

        let tag = monitor.primary ? "主屏" : "外接"
        let number = "\(monitor.index + 1)" as NSString
        let numberFont = NSFont.systemFont(ofSize: 120, weight: .bold)
        let numberAttrs: [NSAttributedString.Key: Any] = [
            .font: numberFont,
            .foregroundColor: NSColor(deviceRed: 59 / 255, green: 130 / 255, blue: 246 / 255, alpha: 1),
        ]
        let numberSize = number.size(withAttributes: numberAttrs)
        let numberOrigin = CGPoint(
            x: (bounds.width - numberSize.width) / 2,
            y: bounds.height / 2 - numberSize.height
        )
        number.draw(at: numberOrigin, withAttributes: numberAttrs)

        let title = "显示器 \(monitor.index + 1)（\(tag)）\n\(monitor.pixelWidth) × \(monitor.pixelHeight)" as NSString
        let para = NSMutableParagraphStyle()
        para.alignment = .center
        let titleAttrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 22, weight: .medium),
            .foregroundColor: NSColor(deviceRed: 232 / 255, green: 234 / 255, blue: 237 / 255, alpha: 1),
            .paragraphStyle: para,
        ]
        let titleRect = CGRect(x: 40, y: numberOrigin.y + numberSize.height + 8, width: bounds.width - 80, height: 80)
        title.draw(in: titleRect, withAttributes: titleAttrs)

        if !monitor.name.isEmpty {
            let name = monitor.name as NSString
            let nameAttrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.monospacedSystemFont(ofSize: 13, weight: .regular),
                .foregroundColor: NSColor(deviceRed: 154 / 255, green: 160 / 255, blue: 166 / 255, alpha: 1),
                .paragraphStyle: para,
            ]
            name.draw(in: CGRect(x: 40, y: titleRect.maxY + 4, width: bounds.width - 80, height: 24), withAttributes: nameAttrs)
        }
    }
}
