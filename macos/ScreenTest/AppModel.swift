import AppKit
import SwiftUI

@Observable
final class AppModel {
    var monitors: [MonitorInfo] = []
    var selectedMonitorID: CGDirectDisplayID?
    var selectedMonitorIndex: Int = 0
    var tab: MainTab = .dead

    var customColor = RGBColor.white
    var autoInterval: Double = 0

    var exportWidth: Int = 1920
    var exportHeight: Int = 1080
    var exportColor = RGBColor.white

    var statusMessage: String?

    private let identifier = IdentifyOverlayController()
    private let session = FullscreenController()

    var selectedMonitor: MonitorInfo? {
        if monitors.indices.contains(selectedMonitorIndex) {
            return monitors[selectedMonitorIndex]
        }
        if let id = selectedMonitorID, let match = monitors.first(where: { $0.id == id }) {
            return match
        }
        return monitors.first
    }

    init() {
        refreshMonitors()
        NotificationCenter.default.addObserver(
            forName: NSApplication.didChangeScreenParametersNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.refreshMonitors()
        }
    }

    func refreshMonitors() {
        let previousID = selectedMonitor?.id ?? selectedMonitorID
        monitors = MonitorService.enumerate()
        if let previousID, let idx = monitors.firstIndex(where: { $0.id == previousID }) {
            selectedMonitorIndex = idx
            selectedMonitorID = previousID
        } else if let idx = monitors.firstIndex(where: { !$0.primary }) {
            selectedMonitorIndex = idx
            selectedMonitorID = monitors[idx].id
        } else {
            selectedMonitorIndex = 0
            selectedMonitorID = monitors.first?.id
        }
    }

    func identifyMonitors() {
        refreshMonitors()
        guard !monitors.isEmpty else {
            statusMessage = "未检测到显示器"
            return
        }
        identifier.show(monitors: monitors)
    }

    func startDeadPixel() {
        open(TestConfiguration.deadPixel(interval: autoInterval))
    }

    func startSolid(_ colors: [RGBColor]) {
        var config = TestConfiguration.deadPixel(interval: autoInterval)
        config.mode = .solid
        config.colors = colors
        open(config)
    }

    func startCustom() {
        var config = TestConfiguration.deadPixel(interval: 0)
        config.mode = .custom
        config.customColor = customColor
        open(config)
    }

    func startGrayCycle() {
        var config = TestConfiguration.deadPixel(interval: autoInterval)
        config.mode = .gray
        open(config)
    }

    func startGraySingle(_ value: UInt8) {
        var config = TestConfiguration.deadPixel(interval: 0)
        config.mode = .custom
        config.customColor = RGBColor(r: value, g: value, b: value)
        open(config)
    }

    func startPattern(_ pattern: PatternKind) {
        var config = TestConfiguration.deadPixel(interval: autoInterval)
        config.mode = .pattern
        config.pattern = pattern
        open(config)
    }

    func startEffect(_ effect: EffectKind) {
        var config = TestConfiguration.deadPixel(interval: 0)
        config.mode = .effect
        config.effect = effect
        open(config)
    }

    func closeTests() {
        identifier.hide()
        session.close()
    }

    func exportImage() {
        let width = exportWidth
        let height = exportHeight
        guard (1...7680).contains(width), (1...4320).contains(height) else {
            presentAlert(title: "错误", message: "分辨率范围: 1–7680 × 1–4320")
            return
        }

        let panel = NSSavePanel()
        panel.title = "保存纯色图片"
        panel.nameFieldStringValue = String(
            format: "solid_%02x%02x%02x_%dx%d.png",
            exportColor.r, exportColor.g, exportColor.b, width, height
        )
        panel.allowedContentTypes = [.png, .jpeg]
        panel.canCreateDirectories = true
        panel.isExtensionHidden = false

        guard panel.runModal() == .OK, let url = panel.url else { return }

        let image = NSImage(size: NSSize(width: width, height: height), flipped: false) { rect in
            self.exportColor.nsColor.setFill()
            rect.fill()
            return true
        }

        guard let tiff = image.tiffRepresentation,
              let rep = NSBitmapImageRep(data: tiff)
        else {
            presentAlert(title: "保存失败", message: "无法生成位图")
            return
        }

        let ext = url.pathExtension.lowercased()
        let type: NSBitmapImageRep.FileType = (ext == "jpg" || ext == "jpeg") ? .jpeg : .png
        let props: [NSBitmapImageRep.PropertyKey: Any] = type == .jpeg ? [.compressionFactor: 0.95] : [:]
        guard let data = rep.representation(using: type, properties: props) else {
            presentAlert(title: "保存失败", message: "无法编码图片")
            return
        }

        do {
            try data.write(to: url)
            presentAlert(title: "完成", message: "已保存:\n\(url.path)\n尺寸: \(width)×\(height)")
        } catch {
            presentAlert(title: "保存失败", message: error.localizedDescription)
        }
    }

    func openSite() {
        NSWorkspace.shared.open(AppInfo.siteURL)
    }

    func applyExportSize(width: Int, height: Int) {
        exportWidth = width
        exportHeight = height
    }

    private func open(_ config: TestConfiguration) {
        refreshMonitors()
        guard let monitor = selectedMonitor else {
            presentAlert(title: "提示", message: "未检测到显示器")
            return
        }
        identifier.hide()
        session.present(config: config, monitor: monitor)
    }

    private func presentAlert(title: String, message: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = .informational
        alert.runModal()
    }
}
