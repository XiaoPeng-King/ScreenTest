#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "[1/3] 生成应用图标…"
python3 "$ROOT/scripts/make_icon.py"

echo "[2/3] 使用 xcodebuild 打包 Release…"
DEST="$ROOT/build"
APP_OUT="$ROOT/dist"
mkdir -p "$DEST" "$APP_OUT"

xcodebuild \
  -project "$ROOT/ScreenTest.xcodeproj" \
  -scheme ScreenTest \
  -configuration Release \
  -derivedDataPath "$DEST" \
  -destination "platform=macOS" \
  CODE_SIGN_IDENTITY="-" \
  CODE_SIGNING_ALLOWED=YES \
  build

APP="$(find "$DEST/Build/Products/Release" -maxdepth 1 -name "ScreenTest.app" -print -quit)"
if [[ -z "${APP}" || ! -d "${APP}" ]]; then
  echo "未找到生成的 ScreenTest.app"
  exit 1
fi

rm -rf "$APP_OUT/ScreenTest.app"
cp -R "$APP" "$APP_OUT/ScreenTest.app"
codesign --force --deep --sign - "$APP_OUT/ScreenTest.app" >/dev/null

echo "[3/3] 完成"
echo
echo "App 路径: $APP_OUT/ScreenTest.app"
du -sh "$APP_OUT/ScreenTest.app"
echo
echo "运行: open \"$APP_OUT/ScreenTest.app\""
