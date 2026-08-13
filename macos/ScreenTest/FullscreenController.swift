import AppKit
import CoreGraphics
import QuartzCore

/// `NSCursor.hide()` 按次数叠加；多藏一次就会在退出全屏后指针消失。
/// 这里只负责把指针恢复为可见，不再隐藏。
enum CursorRestore {
    static func show() {
        NSCursor.setHiddenUntilMouseMoves(false)
        NSCursor.unhide()
    }
}

/// 无边框窗口默认不能成为 key，系统还会把 frame 收进菜单栏以下的 visibleFrame。
/// 主屏测试时这两点都会导致窗口被拽回控制面板所在屏，看起来像“主屏没变化”。
final class OverlayWindow: NSWindow {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }

    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect {
        frameRect
    }
}

final class FullscreenController {
    private var window: OverlayWindow?
    private var host: TestHostView?
    private var localMonitor: Any?
    private var globalMonitor: Any?
    private var hiddenWindows: [NSWindow] = []
    private var placedOnScreenID: CGDirectDisplayID?

    func present(config: TestConfiguration, monitor: MonitorInfo) {
        close()
        guard let screen = MonitorService.screen(for: monitor) else { return }

        let win = OverlayWindow(
            contentRect: CGRect(origin: .zero, size: screen.frame.size),
            styleMask: .borderless,
            backing: .buffered,
            defer: false,
            screen: screen
        )
        win.isOpaque = true
        win.hasShadow = false
        win.backgroundColor = .black
        win.level = NSWindow.Level(rawValue: Int(CGWindowLevelForKey(.screenSaverWindow)))
        win.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary, .ignoresCycle]
        win.ignoresMouseEvents = false
        win.acceptsMouseMovedEvents = true
        win.isReleasedWhenClosed = false
        win.animationBehavior = .none
        win.hidesOnDeactivate = false
        win.isRestorable = false

        let view = TestHostView(configuration: config, monitor: monitor)
        view.onClose = { [weak self] in
            self?.close()
        }
        win.contentView = view
        pin(win, to: screen)

        // 只藏「和测试屏重叠」的控制窗口。副屏上的主界面必须留着，方便边看主屏边操作。
        hideWindows(on: screen, except: win)

        win.orderFrontRegardless()
        win.makeKeyAndOrderFront(nil)
        win.makeFirstResponder(view)
        NSApp.activate(ignoringOtherApps: true)
        pin(win, to: screen)

        // makeKeyAndOrderFront 有时会把窗口弹回当前 key window 所在屏，下一拍再钉一次。
        DispatchQueue.main.async { [weak self, weak win] in
            guard let self, let win, self.window === win else { return }
            let target = MonitorService.screen(forID: monitor.id) ?? screen
            self.pin(win, to: target)
            win.orderFrontRegardless()
            win.makeKey()
            win.makeFirstResponder(view)
        }

        window = win
        host = view
        placedOnScreenID = monitor.id
        installMonitors()
        CursorRestore.show()
    }

    func close() {
        removeMonitors()
        host?.shutdown()
        host = nil
        if let window {
            window.orderOut(nil)
            window.contentView = nil
        }
        window = nil
        placedOnScreenID = nil
        restoreOtherWindows()
        CursorRestore.show()
    }

    private func pin(_ window: NSWindow, to screen: NSScreen) {
        window.setFrame(screen.frame, display: true)
        if window.screen != screen {
            window.setFrameOrigin(screen.frame.origin)
            window.setContentSize(screen.frame.size)
            window.setFrame(screen.frame, display: true)
        }
    }

    private func hideWindows(on screen: NSScreen, except keep: NSWindow) {
        hiddenWindows = NSApp.windows.filter { window in
            window !== keep
                && window.isVisible
                && !(window is OverlayWindow)
                && overlaps(window, screen)
        }
        hiddenWindows.forEach { $0.orderOut(nil) }
    }

    private func overlaps(_ window: NSWindow, _ screen: NSScreen) -> Bool {
        if let current = window.screen, current == screen {
            return true
        }
        return window.frame.intersects(screen.frame)
    }

    private func restoreOtherWindows() {
        for window in hiddenWindows {
            window.orderFront(nil)
        }
        hiddenWindows.removeAll()
    }

    private func installMonitors() {
        localMonitor = NSEvent.addLocalMonitorForEvents(matching: [.keyDown]) { [weak self] event in
            guard let host = self?.host else { return event }
            if host.handleKey(event) {
                return nil
            }
            return event
        }
        globalMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.keyDown]) { [weak self] event in
            if event.keyCode == 53 {
                self?.close()
            }
        }
    }

    private func removeMonitors() {
        if let localMonitor {
            NSEvent.removeMonitor(localMonitor)
            self.localMonitor = nil
        }
        if let globalMonitor {
            NSEvent.removeMonitor(globalMonitor)
            self.globalMonitor = nil
        }
    }
}
