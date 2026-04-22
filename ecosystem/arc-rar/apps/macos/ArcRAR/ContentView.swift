import SwiftUI

struct ContentView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Arc-RAR")
                .font(.largeTitle)
                .bold()
            HStack {
                Button("Open Sample") {
                    viewModel.openArchive(path: "/tmp/demo.rar")
                }
                Button("Refresh Status") {
                    viewModel.refreshStatus()
                }
            }
            Text("Status: \(viewModel.status)")
                .font(.system(.body, design: .monospaced))
            List(viewModel.events, id: \.self) { line in
                Text(line).font(.system(.caption, design: .monospaced))
            }
        }
        .padding(16)
        .frame(minWidth: 700, minHeight: 480)
    }
}
