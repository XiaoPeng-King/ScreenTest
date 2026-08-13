import AppKit
import SwiftUI

@main
struct ScreenTestApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @State private var model = AppModel()

    var body: some Scene {
        Window(AppInfo.title, id: "main") {
            ContentView()
                .environment(model)
                .background(WindowConfigurator())
        }
        .defaultSize(width: 920, height: 720)
        .windowResizability(.contentMinSize)
        .commands {
            CommandGroup(replacing: .newItem) {}
            CommandGroup(after: .appInfo) {
                Button("打开个人网站") { model.openSite() }
            }
            CommandMenu("测试") {
                Button("刷新显示器") { model.refreshMonitors() }
                    .keyboardShortcut("r", modifiers: [.command])
                Button("识别显示器") { model.identifyMonitors() }
                    .keyboardShortcut("i", modifiers: [.command])
                Divider()
                Button("退出全屏测试") { model.closeTests() }
            }
        }
    }
}

/// Force the main window into dark appearance and a sensible minimum size.
private struct WindowConfigurator: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            guard let window = view.window else { return }
            window.title = "\(AppInfo.title) v\(AppInfo.version)"
            window.minSize = NSSize(width: 800, height: 600)
            window.appearance = NSAppearance(named: .darkAqua)
            window.titlebarAppearsTransparent = false
            window.backgroundColor = NSColor(deviceRed: 15 / 255, green: 17 / 255, blue: 21 / 255, alpha: 1)
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {}
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.appearance = NSAppearance(named: .darkAqua)
        CursorRestore.show()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationWillTerminate(_ notification: Notification) {
        CursorRestore.show()
    }
}
