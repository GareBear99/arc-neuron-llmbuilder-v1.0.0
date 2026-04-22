import SwiftUI

@main
struct ArcRARApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView(viewModel: AppViewModel())
        }
    }
}
