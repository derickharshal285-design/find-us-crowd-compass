#!/usr/bin/env bash
# One-command verification for the iOS app + engine.
# Needs: macOS + Xcode + xcodegen (brew install xcodegen).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== generating Xcode project =="
xcodegen generate --spec project.yml --project .

echo "== running engine parity battery (no device needed) =="
xcrun xcodebuild test \
  -project FindUsCrowd.xcodeproj \
  -scheme FindUsApp \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -only-testing:FindUsEngineTests

echo "== building the app for a device =="
xcrun xcodebuild build \
  -project FindUsCrowd.xcodeproj \
  -scheme FindUsApp \
  -destination 'generic/platform=iOS' \
  -configuration Debug