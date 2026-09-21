// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "FindUsCrowd",
    platforms: [
        .iOS(.v16), .macOS(.v13),
    ],
    products: [
        .library(name: "FindUsEngine", targets: ["FindUsEngine"]),
        .library(name: "FindUsBLE", targets: ["FindUsBLE"]),
    ],
    targets: [
        .target(name: "FindUsEngine", path: "Sources/FindUsEngine"),
        .target(name: "FindUsBLE", dependencies: ["FindUsEngine"],
                path: "Sources/FindUsBLE"),
        .testTarget(name: "FindUsEngineTests", dependencies: ["FindUsEngine"],
                    path: "Tests/FindUsEngineTests"),
    ]
)