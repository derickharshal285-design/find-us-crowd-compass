import Foundation

/// Trickle advertisement scheduler — rotates frames so a crowd of 50k hears
/// us with O(k) frames/second per device, never a burst (mirrors core/crowd.py).
public actor AdvScheduler {
    private let windowMs: UInt64
    private var frames: [Data] = []
    private var idx = 0
    private var task: Task<Void, Never>?

    public init(windowMs: UInt64 = 1_200) {
        self.windowMs = windowMs
    }

    public func setFrames(_ frames: [Data]) {
        self.frames = frames
        idx = min(idx, max(0, frames.count - 1))
        task?.cancel()
        guard !frames.isEmpty else { return }
        task = Task { [weak self] in
            await self?.runLoop()
        }
    }

    public func currentFrame() -> Data? {
        frames.isEmpty ? nil : frames[idx % frames.count]
    }

    public func stop() {
        task?.cancel()
        frames = []
    }

    private func runLoop() async {
        while !Task.isCancelled {
            if !frames.isEmpty { idx = (idx + 1) % frames.count }
            try? await Task.sleep(nanoseconds: (windowMs + windowMs / 4) * 1_000_000)
            if !frames.isEmpty { idx = (idx + 1) % frames.count }
        }
    }
}