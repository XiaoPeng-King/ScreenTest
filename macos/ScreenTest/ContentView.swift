import CoreGraphics
import SwiftUI

struct ContentView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model

        VStack(spacing: 0) {
            header
            tip
            monitorBar
            tabBar
            tabBody
            footer
        }
        .background(Theme.bg)
        .foregroundStyle(Theme.text)
        .frame(minWidth: 800, minHeight: 600)
        .preferredColorScheme(.dark)
        .onAppear { model.refreshMonitors() }
    }

    private var header: some View {
        HStack(alignment: .firstTextBaseline) {
            Text("ScreenTest")
                .font(.system(size: 28, weight: .bold))
            Text("本地屏幕测试 · 坏点 · 色彩 · 屏保 · 纯色导出")
                .font(.system(size: 13))
                .foregroundStyle(Theme.muted)
                .padding(.top, 6)
            Spacer()
            Text("v\(AppInfo.version)")
                .font(.system(size: 13))
                .foregroundStyle(Theme.muted)
        }
        .padding(.horizontal, 24)
        .padding(.top, 20)
        .padding(.bottom, 8)
    }

    private var tip: some View {
        Text("提示：进入全屏后按 Esc 退出 · 空格/左键下一页 · 右键/← 上一页 · A 开关自动循环")
            .font(.system(size: 12))
            .foregroundStyle(Theme.muted)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 24)
            .padding(.bottom, 8)
    }

    private var monitorBar: some View {
        HStack(spacing: 10) {
            Text("测试目标显示器")
                .font(.system(size: 13, weight: .semibold))

            Picker("", selection: Bindable(model).selectedMonitorIndex) {
                ForEach(Array(model.monitors.enumerated()), id: \.element.id) { index, monitor in
                    Text(monitor.label).tag(index)
                }
            }
            .labelsHidden()
            .frame(minWidth: 320, maxWidth: 460)
            .onChange(of: model.selectedMonitorIndex) { _, index in
                if model.monitors.indices.contains(index) {
                    model.selectedMonitorID = model.monitors[index].id
                }
            }

            Button("刷新") { model.refreshMonitors() }
                .buttonStyle(QuietButtonStyle())

            Button("识别显示器") { model.identifyMonitors() }
                .buttonStyle(AccentButtonStyle())

            Text("外接屏请在此选择后再开始测试")
                .font(.system(size: 12))
                .foregroundStyle(Theme.muted)

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(Theme.card)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .padding(.horizontal, 24)
        .padding(.bottom, 12)
    }

    private var tabBar: some View {
        HStack(spacing: 6) {
            ForEach(MainTab.allCases) { tab in
                Button {
                    model.tab = tab
                } label: {
                    Text(tab.rawValue)
                        .font(.system(size: 13, weight: model.tab == tab ? .semibold : .regular))
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(model.tab == tab ? Theme.accent : Theme.card)
                        .foregroundStyle(model.tab == tab ? Color.white : Theme.text)
                        .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 8)
    }

    @ViewBuilder
    private var tabBody: some View {
        ScrollView {
            Group {
                switch model.tab {
                case .dead: DeadPixelTab()
                case .color: ColorGrayTab()
                case .pattern: PatternTab()
                case .effect: EffectTab()
                case .export: ExportTab()
                }
            }
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Theme.card)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .padding(.horizontal, 24)
        .padding(.bottom, 12)
    }

    private var footer: some View {
        HStack {
            HStack(spacing: 4) {
                Text("个人网站：")
                    .foregroundStyle(Theme.muted)
                Button(AppInfo.siteDisplay) { model.openSite() }
                    .buttonStyle(.plain)
                    .foregroundStyle(Theme.accent)
                    .underline()
                Text("  ·  本程序完全本地运行，无需联网")
                    .foregroundStyle(Theme.muted)
            }
            .font(.system(size: 12))

            Spacer()

            HStack(spacing: 8) {
                Text("自动切换间隔(秒，0=手动):")
                    .font(.system(size: 12))
                    .foregroundStyle(Theme.muted)
                TextField("", value: Bindable(model).autoInterval, format: .number.precision(.fractionLength(1)))
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 56)
                    .onChange(of: model.autoInterval) { _, value in
                        model.autoInterval = min(30, max(0, (value * 2).rounded() / 2))
                    }
                Stepper("", value: Bindable(model).autoInterval, in: 0...30, step: 0.5)
                    .labelsHidden()
            }
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 16)
    }
}

struct ColorChip: View {
    let name: String
    let rgb: RGBColor
    var compact: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack {
                rgb.color
                if !compact {
                    Text(name)
                        .font(.system(size: 12))
                        .foregroundStyle(rgb.contrasting.color)
                }
            }
            .frame(width: compact ? 28 : 72, height: compact ? 22 : 56)
            .overlay(
                RoundedRectangle(cornerRadius: 3)
                    .stroke(Theme.accent, lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
        .help(name)
    }
}

struct QuietButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12))
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(configuration.isPressed ? Theme.accent : Theme.control)
            .foregroundStyle(Theme.text)
            .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
    }
}

struct AccentButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12, weight: .semibold))
            .padding(.horizontal, 12)
            .padding(.vertical, 5)
            .background(configuration.isPressed ? Theme.accentDark : Theme.accent)
            .foregroundStyle(.white)
            .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    var prominent: Bool = true

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 14, weight: prominent ? .semibold : .regular))
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(configuration.isPressed ? Theme.accentDark : (prominent ? Theme.accent : Theme.control))
            .foregroundStyle(.white)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}
