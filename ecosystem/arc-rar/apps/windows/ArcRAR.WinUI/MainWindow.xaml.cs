using Microsoft.UI.Xaml;
using System.Diagnostics;

namespace ArcRAR.WinUI;

public sealed partial class MainWindow : Window
{
    public MainWindow()
    {
        this.InitializeComponent();
    }

    private void OpenSample_Click(object sender, RoutedEventArgs e)
    {
        OutputBox.Text = RunArcRar("gui open C:\\temp\\demo.rar --json");
    }

    private void RefreshStatus_Click(object sender, RoutedEventArgs e)
    {
        OutputBox.Text = RunArcRar("gui status --json");
    }

    private static string RunArcRar(string arguments)
    {
        try
        {
            var start = new ProcessStartInfo("arc-rar", arguments)
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            using var process = Process.Start(start)!;
            var stdout = process.StandardOutput.ReadToEnd();
            var stderr = process.StandardError.ReadToEnd();
            process.WaitForExit();
            return string.IsNullOrWhiteSpace(stderr) ? stdout : stdout + "\n" + stderr;
        }
        catch (System.Exception ex)
        {
            return $"{{\"ok\":false,\"error\":\"{ex.Message}\"}}";
        }
    }
}
