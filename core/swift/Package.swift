// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "FindUsPacket",
    platforms: [
        .iOS(.v15),
        .macOS(.v12)
    ],
    products: [
        .library(name: "FindUsPacket", targets: ["FindUsPacket"])
    ],
    targets: [
        .target(name: "FindUsPacket", dependencies: []),
        .testTarget(name: "FindUsPacketTests", dependencies: ["FindUsPacket"])
    ]
)