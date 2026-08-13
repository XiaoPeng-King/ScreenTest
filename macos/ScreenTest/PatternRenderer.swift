import CoreGraphics
import Darwin
import Foundation

enum PatternRenderer {
    static func checker(width: Int, height: Int) -> CGImage? {
        let cell = 40
        return makeImage(width: width, height: height) { px, x, y in
            let on = ((x / cell) + (y / cell)) % 2 == 0
            let v: UInt8 = on ? 255 : 0
            px[0] = v; px[1] = v; px[2] = v; px[3] = 255
        }
    }

    static func hline(width: Int, height: Int) -> CGImage? {
        makeImage(width: width, height: height) { px, _, y in
            let v: UInt8 = (y & 1) == 0 ? 255 : 0
            px[0] = v; px[1] = v; px[2] = v; px[3] = 255
        }
    }

    static func vline(width: Int, height: Int) -> CGImage? {
        makeImage(width: width, height: height) { px, x, _ in
            let v: UInt8 = (x & 1) == 0 ? 255 : 0
            px[0] = v; px[1] = v; px[2] = v; px[3] = 255
        }
    }

    static func dots(width: Int, height: Int) -> CGImage? {
        let step = 30
        let radius = 3
        return makeImage(width: width, height: height) { px, x, y in
            let cx = step / 2 + ((x) / step) * step
            let cy = step / 2 + ((y) / step) * step
            let dx = x - cx
            let dy = y - cy
            let on = dx * dx + dy * dy <= radius * radius
            let v: UInt8 = on ? 255 : 0
            px[0] = v; px[1] = v; px[2] = v; px[3] = 255
        }
    }

    static func gradient(kind: PatternKind, width: Int, height: Int) -> CGImage? {
        makeImage(width: width, height: height) { px, x, y in
            let color: (UInt8, UInt8, UInt8)
            switch kind {
            case .gradientGray:
                let t = width <= 1 ? 0 : Int(round(Double(x) / Double(width - 1) * 255))
                let v = UInt8(clamping: t)
                color = (v, v, v)
            case .gradientH:
                color = rgbSweep(position: width <= 1 ? 0 : Double(x) / Double(width - 1))
            case .gradientV:
                let t = height <= 1 ? 0 : Double(y) / Double(height - 1)
                color = (
                    UInt8(clamping: Int(255 * (1 - t))),
                    UInt8(clamping: Int(255 * abs(0.5 - t) * 2)),
                    UInt8(clamping: Int(255 * t))
                )
            default:
                color = (0, 0, 0)
            }
            px[0] = color.0
            px[1] = color.1
            px[2] = color.2
            px[3] = 255
        }
    }

    static func noise(width: Int, height: Int) -> CGImage? {
        // Tiny field, then nearest-neighbor upscale keeps the snowflake look without 4K cost.
        let sw = 160
        let sh = 90
        guard let small = makeImage(width: sw, height: sh, fill: 0, plot: { px, _, _ in
            let v = UInt8.random(in: 0...255)
            px[0] = v; px[1] = v; px[2] = v; px[3] = 255
        }) else { return nil }

        guard let ctx = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: 0,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }
        ctx.interpolationQuality = .none
        ctx.draw(small, in: CGRect(x: 0, y: 0, width: width, height: height))
        return ctx.makeImage()
    }

    private static func rgbSweep(position: Double) -> (UInt8, UInt8, UInt8) {
        let x = max(0, min(1, position)) * 3
        if x < 1 {
            return (255, UInt8(clamping: Int(255 * x)), 0)
        }
        if x < 2 {
            let t = x - 1
            return (UInt8(clamping: Int(255 * (1 - t))), 255, UInt8(clamping: Int(255 * t)))
        }
        let t = x - 2
        return (0, UInt8(clamping: Int(255 * (1 - t))), 255)
    }

    private static func makeImage(
        width: Int,
        height: Int,
        fill: UInt8 = 0,
        plot: (UnsafeMutablePointer<UInt8>, Int, Int) -> Void
    ) -> CGImage? {
        let w = max(1, width)
        let h = max(1, height)
        guard let ctx = CGContext(
            data: nil,
            width: w,
            height: h,
            bitsPerComponent: 8,
            bytesPerRow: 0,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }

        guard let data = ctx.data else { return nil }
        let ptr = data.assumingMemoryBound(to: UInt8.self)
        let bpr = ctx.bytesPerRow

        if fill == 0 {
            memset(ptr, 0, bpr * h)
        }

        for y in 0..<h {
            // CG bitmaps are bottom-up; flip so y=0 is the top of the screen.
            let rowIndex = h - 1 - y
            let row = ptr.advanced(by: rowIndex * bpr)
            for x in 0..<w {
                plot(row.advanced(by: x * 4), x, y)
            }
        }
        return ctx.makeImage()
    }
}
