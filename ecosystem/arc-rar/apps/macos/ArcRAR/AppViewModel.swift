import Foundation
import SwiftUI

final class AppViewModel: ObservableObject {
    @Published var status: String = "idle"
    @Published var events: [String] = []

    func openArchive(path: String) {
        let payload = ["archive": path]
        let result = CLIBridge.run(arguments: ["gui", "open", path, "--json"])
        status = result
        events.insert(result, at: 0)
    }

    func refreshStatus() {
        let result = CLIBridge.run(arguments: ["gui", "status", "--json"])
        status = result
        events.insert(result, at: 0)
    }
}
