import AppKit

final class TestHostView: NSView {
    var onClose: (() -> Void)?

    private var config: TestConfiguration
    private let monitor: MonitorInfo
    private var index: Int = 0
    private var autoInterval: TimeInterval
    private var running = true

    private var autoTimer: Timer?
    private var animTimer: Timer?
    private var hintHideWork: DispatchWorkItem?
    private var navLockUntil: TimeInterval = 0
    private var hintVisible = true
    private var hintText = ""

    private var bounce = BounceState()
    private var matrix = MatrixState()
    private var noiseFrame = 0
    private var cachedImage: CGImage?
    private var cachedKey = ""
    private var trailImage: NSImage?

    init(configuration: TestConfiguration, monitor: MonitorInfo) {
        self.config = configuration
        self.monitor = monitor
        self.autoInterval = configuration.autoInterval
        super.init(frame: monitor.frame)
        wantsLayer = true
        layer?.isOpaque = true
        hintText = defaultHint
        if let start = configuration.grayStart,
           let idx = GrayLevels.all.firstIndex(of: start) {
            index = idx
        }
        scheduleHintHide()
        if autoInterval > 0 {
            startAuto()
        }
        if config.mode == .effect {
            startEffect()
        }
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override var isFlipped: Bool { true }
    override var acceptsFirstResponder: Bool { true }
    override var isOpaque: Bool { true }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        window?.makeFirstResponder(self)
        CursorRestore.show()
    }

    func shutdown() {
        running = false
        autoTimer?.invalidate()
        animTimer?.invalidate()
        autoTimer = nil
        animTimer = nil
        hintHideWork?.cancel()
        cachedImage = nil
        trailImage = nil
    }

    @discardableResult
    func handleKey(_ event: NSEvent) -> Bool {
        switch event.keyCode {
        case 53, 103: // Esc, F11
            closeTest()
            return true
        case 49, 124: // space, right
            if navAllowed() { nextItem() }
            return true
        case 123: // left
            if navAllowed() { prevItem() }
            return true
        default:
            if let chars = event.charactersIgnoringModifiers?.lowercased(), chars == "a" {
                if navAllowed() { toggleAuto() }
                return true
            }
            return false
        }
    }

    override func mouseDown(with event: NSEvent) {
        if navAllowed() { nextItem() }
    }

    override func rightMouseDown(with event: NSEvent) {
        if navAllowed() { prevItem() }
    }

    override func keyDown(with event: NSEvent) {
        if !handleKey(event) {
            super.keyDown(with: event)
        }
    }

    private var defaultHint: String {
        "Esc 退出  |  空格/点击 下一页  |  ← → 切换  |  A 自动循环  |  显示器 \(monitor.index + 1) \(monitor.pixelWidth)×\(monitor.pixelHeight)"
    }

    private func navAllowed() -> Bool {
        let now = ProcessInfo.processInfo.systemUptime
        if now < navLockUntil { return false }
        navLockUntil = now + 0.12
        return true
    }

    private func closeTest() {
        shutdown()
        onClose?()
    }

    private func nextItem() {
        switch config.mode {
        case .solid, .deadPixel, .gray:
            index = (index + 1) % max(1, itemCount)
            cachedImage = nil
            needsDisplay = true
        case .pattern:
            let all = PatternKind.allCases
            let current = all.firstIndex(of: config.pattern) ?? 0
            config.pattern = all[(current + 1) % all.count]
            cachedImage = nil
            needsDisplay = true
        case .custom, .effect:
            break
        }
    }

    private func prevItem() {
        switch config.mode {
        case .solid, .deadPixel, .gray:
            let n = max(1, itemCount)
            index = (index - 1 + n) % n
            cachedImage = nil
            needsDisplay = true
        case .pattern:
            let all = PatternKind.allCases
            let current = all.firstIndex(of: config.pattern) ?? 0
            config.pattern = all[(current - 1 + all.count) % all.count]
            cachedImage = nil
            needsDisplay = true
        case .custom, .effect:
            break
        }
    }

    private var itemCount: Int {
        switch config.mode {
        case .gray: return GrayLevels.all.count
        case .solid, .deadPixel: return max(1, config.colors.count)
        default: return 1
        }
    }

    private func toggleAuto() {
        if autoInterval > 0 {
            autoInterval = 0
            autoTimer?.invalidate()
            autoTimer = nil
            showHint("自动循环：关")
        } else {
            autoInterval = 2.0
            startAuto()
            showHint("自动循环：开（每 2 秒）")
        }
    }

    private func startAuto() {
        autoTimer?.invalidate()
        guard autoInterval > 0 else { return }
        let timer = Timer(timeInterval: autoInterval, repeats: true) { [weak self] _ in
            DispatchQueue.main.async {
                self?.nextItem()
            }
        }
        RunLoop.main.add(timer, forMode: .common)
        autoTimer = timer
    }

    private func startEffect() {
        animTimer?.invalidate()
        switch config.effect {
        case .dim:
            break
        case .bouncing:
            bounce = BounceState(x: bounds.width / 4, y: bounds.height / 4, dx: 4, dy: 3)
            startAnim(1.0 / 60.0)
        case .matrix:
            let cols = max(1, Int(bounds.width / 16))
            let rows = max(1, Int(bounds.height / 16))
            matrix = MatrixState(drops: (0..<cols).map { _ in Int.random(in: 0...rows) })
            startAnim(0.05)
        case .noise:
            startAnim(0.05)
        }
    }

    private func startAnim(_ interval: TimeInterval) {
        let timer = Timer(timeInterval: interval, repeats: true) { [weak self] _ in
            DispatchQueue.main.async {
                self?.tick()
            }
        }
        RunLoop.main.add(timer, forMode: .common)
        animTimer = timer
    }

    private func tick() {
        guard running, config.mode == .effect else { return }
        switch config.effect {
        case .bouncing:
            bounce.advance(in: bounds.size)
        case .matrix:
            matrix.advance(height: bounds.height)
        case .noise:
            noiseFrame += 1
            cachedImage = nil
        case .dim:
            return
        }
        needsDisplay = true
    }

    private func showHint(_ text: String, duration: TimeInterval = 2.0) {
        hintText = text
        hintVisible = true
        needsDisplay = true
        scheduleHintHide(after: duration)
    }

    private func scheduleHintHide(after delay: TimeInterval = 3.5) {
        hintHideWork?.cancel()
        let work = DispatchWorkItem { [weak self] in
            self?.hintVisible = false
            self?.needsDisplay = true
        }
        hintHideWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: work)
    }

    // MARK: - Drawing

    override func draw(_ dirtyRect: NSRect) {
        guard let context = NSGraphicsContext.current?.cgContext else { return }
        context.interpolationQuality = .none

        switch config.mode {
        case .effect:
            drawEffect(in: context)
        case .custom:
            fill(config.customColor)
        case .gray:
            let g = GrayLevels.all[index % GrayLevels.all.count]
            let color = RGBColor(r: g, g: g, b: g)
            fill(color)
            drawCornerLabel("灰度 \(g)/255", color: color)
        case .solid, .deadPixel:
            let color = config.colors[index % max(1, config.colors.count)]
            fill(color)
            let name = SolidPresets.name(for: color)
            drawCornerLabel("\(name)  (\(index + 1)/\(config.colors.count))", color: color)
        case .pattern:
            drawPattern(in: context)
        }

        if hintVisible {
            drawHint()
        }
    }

    private func fill(_ color: RGBColor) {
        color.nsColor.setFill()
        bounds.fill()
    }

    private func drawPattern(in context: CGContext) {
        RGBColor.black.nsColor.setFill()
        bounds.fill()

        switch config.pattern {
        case .checker:
            drawCached(key: "checker") { PatternRenderer.checker(width: $0, height: $1) }
            drawCornerLabel(config.pattern.overlayLabel, color: .black)
        case .grid:
            drawGrid()
            drawCornerLabel(config.pattern.overlayLabel, color: .black)
        case .hline:
            drawCached(key: "hline") { PatternRenderer.hline(width: $0, height: $1) }
            drawCornerLabel(config.pattern.overlayLabel, color: .black)
        case .vline:
            drawCached(key: "vline") { PatternRenderer.vline(width: $0, height: $1) }
            drawCornerLabel(config.pattern.overlayLabel, color: .black)
        case .crosshatch:
            drawCrosshatch()
            drawCornerLabel(config.pattern.overlayLabel, color: .black)
        case .colorbars:
            drawColorBars()
            drawCornerLabel(config.pattern.overlayLabel, color: .black)
        case .gradientH, .gradientV, .gradientGray:
            drawCached(key: config.pattern.rawValue) { w, h in
                PatternRenderer.gradient(kind: self.config.pattern, width: w, height: h)
            }
            drawCornerLabel(config.pattern.overlayLabel, color: .black)
        case .dots:
            drawCached(key: "dots") { PatternRenderer.dots(width: $0, height: $1) }
            drawCornerLabel(config.pattern.overlayLabel, color: .black)
        case .textFocus:
            drawTextFocus()
        }
    }

    private func drawCached(key: String, builder: (Int, Int) -> CGImage?) {
        let scale = window?.backingScaleFactor ?? monitor.scale
        let pw = max(1, Int((bounds.width * scale).rounded()))
        let ph = max(1, Int((bounds.height * scale).rounded()))
        let cacheKey = "\(key)-\(pw)x\(ph)"
        if cachedKey != cacheKey {
            cachedImage = builder(pw, ph)
            cachedKey = cacheKey
        }
        guard let image = cachedImage else { return }
        let nsimg = NSImage(cgImage: image, size: bounds.size)
        nsimg.draw(
            in: bounds,
            from: .zero,
            operation: .copy,
            fraction: 1,
            respectFlipped: true,
            hints: [.interpolation: NSImageInterpolation.none]
        )
    }

    private func drawGrid() {
        let step: CGFloat = 50
        NSColor(deviceRed: 0, green: 1, blue: 0, alpha: 1).setStroke()
        let grid = NSBezierPath()
        grid.lineWidth = 1
        var x: CGFloat = 0
        while x <= bounds.width {
            grid.move(to: NSPoint(x: x + 0.5, y: 0))
            grid.line(to: NSPoint(x: x + 0.5, y: bounds.height))
            x += step
        }
        var y: CGFloat = 0
        while y <= bounds.height {
            grid.move(to: NSPoint(x: 0, y: y + 0.5))
            grid.line(to: NSPoint(x: bounds.width, y: y + 0.5))
            y += step
        }
        grid.stroke()

        NSColor(deviceRed: 1, green: 0, blue: 0, alpha: 1).setStroke()
        let cross = NSBezierPath()
        cross.lineWidth = 2
        cross.move(to: NSPoint(x: bounds.midX, y: 0))
        cross.line(to: NSPoint(x: bounds.midX, y: bounds.height))
        cross.move(to: NSPoint(x: 0, y: bounds.midY))
        cross.line(to: NSPoint(x: bounds.width, y: bounds.midY))
        cross.stroke()
    }

    private func drawCrosshatch() {
        NSColor(deviceWhite: 0.53, alpha: 1).setStroke()
        let path = NSBezierPath()
        path.lineWidth = 1
        let h = bounds.height
        let w = bounds.width
        var i: CGFloat = -h
        while i < w {
            path.move(to: NSPoint(x: i, y: 0))
            path.line(to: NSPoint(x: i + h, y: h))
            path.move(to: NSPoint(x: i, y: h))
            path.line(to: NSPoint(x: i + h, y: 0))
            i += 20
        }
        path.stroke()
    }

    private func drawColorBars() {
        let bars: [RGBColor] = [
            .white,
            RGBColor(r: 255, g: 255, b: 0),
            RGBColor(r: 0, g: 255, b: 255),
            RGBColor(r: 0, g: 255, b: 0),
            RGBColor(r: 255, g: 0, b: 255),
            RGBColor(r: 255, g: 0, b: 0),
            RGBColor(r: 0, g: 0, b: 255),
            .black,
        ]
        let bw = bounds.width / CGFloat(bars.count)
        for (i, color) in bars.enumerated() {
            let rect = NSRect(
                x: CGFloat(i) * bw,
                y: 0,
                width: i == bars.count - 1 ? bounds.width - CGFloat(i) * bw : bw,
                height: bounds.height
            )
            color.nsColor.setFill()
            rect.fill()
        }
    }

    private func drawTextFocus() {
        NSColor.white.setFill()
        bounds.fill()
        let sample = "Aa Bb Cc  清晰度测试  The quick brown fox jumps over the lazy dog"
        let sizes: [CGFloat] = [10, 12, 14, 16, 20, 24, 32, 48]
        var y: CGFloat = 40
        for size in sizes {
            let font = NSFont.monospacedSystemFont(ofSize: size, weight: .regular)
            let attrs: [NSAttributedString.Key: Any] = [
                .font: font,
                .foregroundColor: NSColor.black,
            ]
            let text = sample as NSString
            let textSize = text.size(withAttributes: attrs)
            text.draw(at: NSPoint(x: (bounds.width - textSize.width) / 2, y: y), withAttributes: attrs)
            y += size + 18
        }
        let footer = "文字清晰度 / 锐度测试" as NSString
        let footerAttrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 18),
            .foregroundColor: NSColor(deviceWhite: 0.2, alpha: 1),
        ]
        let fs = footer.size(withAttributes: footerAttrs)
        footer.draw(at: NSPoint(x: (bounds.width - fs.width) / 2, y: bounds.height - 80), withAttributes: footerAttrs)
    }

    private func drawEffect(in context: CGContext) {
        switch config.effect {
        case .dim:
            fill(.black)
            drawCornerLabel("暗屏屏保（Esc 退出）", color: RGBColor(r: 20, g: 20, b: 20))
        case .bouncing:
            NSColor(deviceWhite: 0.067, alpha: 1).setFill()
            bounds.fill()
            let colors: [NSColor] = [
                NSColor(deviceRed: 1, green: 0, blue: 0, alpha: 1),
                NSColor(deviceRed: 0, green: 1, blue: 0, alpha: 1),
                NSColor(deviceRed: 0, green: 0.67, blue: 1, alpha: 1),
                NSColor(deviceRed: 1, green: 0.67, blue: 0, alpha: 1),
                NSColor(deviceRed: 1, green: 0, blue: 1, alpha: 1),
                .white,
            ]
            let text = "ScreenTest" as NSString
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: 28, weight: .bold),
                .foregroundColor: colors[bounce.colorIndex % colors.count],
            ]
            text.draw(at: NSPoint(x: bounce.x, y: bounce.y), withAttributes: attrs)
        case .matrix:
            drawMatrixRain()
        case .noise:
            drawCached(key: "noise-\(noiseFrame)") { w, h in
                PatternRenderer.noise(width: w, height: h)
            }
        }
    }

    private func drawMatrixRain() {
        if trailImage == nil || trailImage?.size != bounds.size {
            let image = NSImage(size: bounds.size)
            image.lockFocusFlipped(true)
            NSColor.black.setFill()
            bounds.fill()
            image.unlockFocus()
            trailImage = image
        }

        trailImage?.lockFocusFlipped(true)
        NSColor.black.withAlphaComponent(0.28).setFill()
        bounds.fill()
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.monospacedSystemFont(ofSize: 12, weight: .regular),
            .foregroundColor: NSColor(deviceRed: 0, green: 1, blue: 0.4, alpha: 1),
        ]
        for (i, drop) in matrix.drops.enumerated() {
            let ch = MatrixState.glyph() as NSString
            ch.draw(at: NSPoint(x: CGFloat(i) * 16, y: CGFloat(drop) * 16), withAttributes: attrs)
        }
        trailImage?.unlockFocus()
        trailImage?.draw(in: bounds, from: .zero, operation: .copy, fraction: 1)
    }

    private func drawCornerLabel(_ text: String, color: RGBColor) {
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 14, weight: .bold),
            .foregroundColor: color.contrasting.nsColor,
        ]
        (text as NSString).draw(at: NSPoint(x: 20, y: 20), withAttributes: attrs)
    }

    private func drawHint() {
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 13),
            .foregroundColor: NSColor.white,
        ]
        let text = hintText as NSString
        let size = text.size(withAttributes: attrs)
        let origin = NSPoint(x: (bounds.width - size.width) / 2, y: bounds.height - 36)
        NSColor.black.withAlphaComponent(0.45).setFill()
        NSRect(x: origin.x - 10, y: origin.y - 6, width: size.width + 20, height: size.height + 10).fill()
        text.draw(at: origin, withAttributes: attrs)
    }
}

private struct BounceState {
    var x: CGFloat = 80
    var y: CGFloat = 80
    var dx: CGFloat = 4
    var dy: CGFloat = 3
    var colorIndex = 0
    var textSize = CGSize(width: 180, height: 40)

    mutating func advance(in size: CGSize) {
        x += dx
        y += dy
        if x <= 0 || x + textSize.width >= size.width {
            dx *= -1
            colorIndex += 1
            x = min(max(0, x), max(0, size.width - textSize.width))
        }
        if y <= 0 || y + textSize.height >= size.height {
            dy *= -1
            colorIndex += 1
            y = min(max(0, y), max(0, size.height - textSize.height))
        }
    }
}

private struct MatrixState {
    var drops: [Int] = []

    static let charset = Array("ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿ01アイウエオﾊﾋﾌﾍﾎ")

    static func glyph() -> String {
        String(charset.randomElement() ?? "0")
    }

    mutating func advance(height: CGFloat) {
        let maxRow = Int(height / 16) + 2
        for i in drops.indices {
            if drops[i] > maxRow, Double.random(in: 0...1) > 0.975 {
                drops[i] = 0
            } else {
                drops[i] += 1
            }
        }
    }
}
