import AppKit
import SwiftUI

struct DeadPixelTab: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("坏点 / 亮点检测")
                .font(.system(size: 20, weight: .bold))

            Text("全屏依次显示纯色背景，仔细观察是否有固定颜色的异常像素点。\n黑色上找亮点 · 白色上找黑点 · RGB 上找卡死子像素。")
                .font(.system(size: 13))
                .foregroundStyle(Theme.muted)
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 10) {
                ForEach(SolidPresets.all.prefix(8)) { preset in
                    ColorChip(name: preset.name, rgb: preset.rgb) {
                        model.startSolid([preset.rgb])
                    }
                }
            }

            HStack(spacing: 12) {
                Button("开始坏点检测（全色循环）") { model.startDeadPixel() }
                    .buttonStyle(PrimaryButtonStyle())
                Button("仅 RGB + 黑白") {
                    model.startSolid([
                        .black, .white,
                        RGBColor(r: 255, g: 0, b: 0),
                        RGBColor(r: 0, g: 255, b: 0),
                        RGBColor(r: 0, g: 0, b: 255),
                    ])
                }
                .buttonStyle(PrimaryButtonStyle(prominent: false))
            }

            Text("建议：在较暗环境、屏幕干净时测试；逐页检查每个角落与边缘。")
                .font(.system(size: 12))
                .foregroundStyle(Theme.faint)
        }
    }
}

struct ColorGrayTab: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model

        VStack(alignment: .leading, spacing: 16) {
            Text("纯色显示 & 灰度亮度")
                .font(.system(size: 20, weight: .bold))

            Text("用于对比度、亮度均匀性、背光漏光（纯黑）和色彩表现评估。")
                .font(.system(size: 13))
                .foregroundStyle(Theme.muted)

            HStack(spacing: 12) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(model.customColor.color)
                    .frame(width: 48, height: 48)
                    .overlay(RoundedRectangle(cornerRadius: 4).stroke(Theme.accent, lineWidth: 2))

                Text("自定义颜色: \(model.customColor.hex)  RGB(\(model.customColor.r),\(model.customColor.g),\(model.customColor.b))")
                    .font(.system(size: 13))

                ColorPicker("", selection: customColorBinding, supportsOpacity: false)
                    .labelsHidden()
                    .frame(width: 36)

                Button("全屏显示此颜色") { model.startCustom() }
                    .buttonStyle(PrimaryButtonStyle())
            }

            VStack(spacing: 8) {
                rgbSlider("R", value: rBinding, tint: .red)
                rgbSlider("G", value: gBinding, tint: .green)
                rgbSlider("B", value: bBinding, tint: .blue)
            }

            Text("灰度等级快速测试")
                .font(.system(size: 15, weight: .semibold))

            HStack(spacing: 6) {
                ForEach(GrayLevels.all, id: \.self) { gray in
                    let rgb = RGBColor(r: gray, g: gray, b: gray)
                    Button("\(gray)") { model.startGraySingle(gray) }
                        .font(.system(size: 11, design: .monospaced))
                        .frame(width: 36, height: 28)
                        .background(rgb.color)
                        .foregroundStyle(rgb.contrasting.color)
                        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                        .buttonStyle(.plain)
                }
            }

            Button("开始灰度循环测试") { model.startGrayCycle() }
                .buttonStyle(PrimaryButtonStyle(prominent: false))

            Text("预设纯色")
                .font(.system(size: 15, weight: .semibold))

            LazyVGrid(columns: [GridItem(.adaptive(minimum: 76), spacing: 10)], alignment: .leading, spacing: 10) {
                ForEach(SolidPresets.all) { preset in
                    ColorChip(name: preset.name, rgb: preset.rgb) {
                        model.startSolid([preset.rgb])
                    }
                }
            }
        }
    }

    private var customColorBinding: Binding<Color> {
        Binding(
            get: { model.customColor.color },
            set: { newValue in
                let ns = NSColor(newValue).usingColorSpace(.deviceRGB) ?? NSColor(newValue)
                model.customColor = RGBColor(
                    r: UInt8(clamping: Int((ns.redComponent * 255).rounded())),
                    g: UInt8(clamping: Int((ns.greenComponent * 255).rounded())),
                    b: UInt8(clamping: Int((ns.blueComponent * 255).rounded()))
                )
            }
        )
    }

    private var rBinding: Binding<Double> {
        Binding(
            get: { Double(model.customColor.r) },
            set: { model.customColor.r = UInt8(clamping: Int($0.rounded())) }
        )
    }

    private var gBinding: Binding<Double> {
        Binding(
            get: { Double(model.customColor.g) },
            set: { model.customColor.g = UInt8(clamping: Int($0.rounded())) }
        )
    }

    private var bBinding: Binding<Double> {
        Binding(
            get: { Double(model.customColor.b) },
            set: { model.customColor.b = UInt8(clamping: Int($0.rounded())) }
        )
    }

    private func rgbSlider(_ label: String, value: Binding<Double>, tint: Color) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundStyle(tint)
                .frame(width: 18)
            Slider(value: value, in: 0...255, step: 1)
                .tint(tint)
            Text("\(Int(value.wrappedValue))")
                .font(.system(size: 12, design: .monospaced))
                .frame(width: 32, alignment: .trailing)
        }
    }
}

struct PatternTab: View {
    @Environment(AppModel.self) private var model

    private let columns = [
        GridItem(.adaptive(minimum: 200), spacing: 12),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("图案与几何测试")
                .font(.system(size: 20, weight: .bold))

            Text("检测几何失真、清晰度、色带（banding）、收敛与面板均匀性。")
                .font(.system(size: 13))
                .foregroundStyle(Theme.muted)

            LazyVGrid(columns: columns, alignment: .leading, spacing: 12) {
                ForEach(PatternKind.allCases) { pattern in
                    Button {
                        model.startPattern(pattern)
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(pattern.title)
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundStyle(Theme.text)
                            Text(pattern.subtitle)
                                .font(.system(size: 12))
                                .foregroundStyle(Theme.muted)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(14)
                        .background(Theme.inner)
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }

            Button("依次浏览全部图案") { model.startPattern(.checker) }
                .buttonStyle(PrimaryButtonStyle())
        }
    }
}

struct EffectTab: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("屏保与特效")
                .font(.system(size: 20, weight: .bold))

            Text("不关显示器时降低亮度或展示动画，保护屏幕并放松眼睛。")
                .font(.system(size: 13))
                .foregroundStyle(Theme.muted)

            ForEach(EffectKind.allCases) { effect in
                Button {
                    model.startEffect(effect)
                } label: {
                    HStack {
                        Text(effect.title)
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundStyle(Theme.text)
                        Text("—  \(effect.subtitle)")
                            .font(.system(size: 13))
                            .foregroundStyle(Theme.muted)
                        Spacer()
                        Text("启动 ›")
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(Theme.accent)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 14)
                    .background(Theme.inner)
                    .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                }
                .buttonStyle(.plain)
            }

            Text("OLED 用户提示：长时间显示静态高亮内容可能造成烙印，建议使用暗屏或动态特效。")
                .font(.system(size: 12))
                .foregroundStyle(Theme.faint)
        }
    }
}

struct ExportTab: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model

        VStack(alignment: .leading, spacing: 16) {
            Text("纯色图片生成与下载")
                .font(.system(size: 20, weight: .bold))

            Text("生成指定分辨率的纯色 PNG，可用于壁纸、设计素材或测试图。")
                .font(.system(size: 13))
                .foregroundStyle(Theme.muted)

            HStack(spacing: 10) {
                Text("宽度")
                TextField("", value: $model.exportWidth, format: .number)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 80)
                Text("高度")
                TextField("", value: $model.exportHeight, format: .number)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 80)

                ForEach(ExportPreset.standard) { preset in
                    Button(preset.title) {
                        model.applyExportSize(width: preset.width, height: preset.height)
                    }
                    .buttonStyle(QuietButtonStyle())
                }

                if let monitor = model.selectedMonitor {
                    Button("当前屏 \(monitor.pixelWidth)×\(monitor.pixelHeight)") {
                        model.applyExportSize(width: monitor.pixelWidth, height: monitor.pixelHeight)
                    }
                    .buttonStyle(QuietButtonStyle())
                }
            }

            HStack(spacing: 12) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(model.exportColor.color)
                    .frame(width: 64, height: 64)
                    .overlay(RoundedRectangle(cornerRadius: 4).stroke(Theme.accent, lineWidth: 2))

                Text("导出颜色: \(model.exportColor.hex)")
                    .font(.system(size: 13))

                ColorPicker("", selection: exportColorBinding, supportsOpacity: false)
                    .labelsHidden()
                    .frame(width: 36)
            }

            HStack(spacing: 8) {
                ForEach(SolidPresets.all.prefix(8)) { preset in
                    ColorChip(name: preset.name, rgb: preset.rgb, compact: true) {
                        model.exportColor = preset.rgb
                    }
                }
            }

            Button("生成并保存 PNG…") { model.exportImage() }
                .buttonStyle(PrimaryButtonStyle())

            if let monitor = model.selectedMonitor {
                Text("当前目标屏分辨率: \(monitor.pixelWidth) × \(monitor.pixelHeight)  ·  缩放 \(monitor.scalePercent)%")
                    .font(.system(size: 12))
                    .foregroundStyle(Theme.faint)
            }
        }
    }

    private var exportColorBinding: Binding<Color> {
        Binding(
            get: { model.exportColor.color },
            set: { newValue in
                let ns = NSColor(newValue).usingColorSpace(.deviceRGB) ?? NSColor(newValue)
                model.exportColor = RGBColor(
                    r: UInt8(clamping: Int((ns.redComponent * 255).rounded())),
                    g: UInt8(clamping: Int((ns.greenComponent * 255).rounded())),
                    b: UInt8(clamping: Int((ns.blueComponent * 255).rounded()))
                )
            }
        )
    }
}
