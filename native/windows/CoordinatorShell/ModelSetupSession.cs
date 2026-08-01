using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace TotalSegmentatorWrapper.Windows.CoordinatorShell;

internal sealed class ModelSetupSession : IDisposable
{
    private const string ProgressPrefix =
        "TOTALSEG_MODEL_PREP_PROGRESS ";
    private readonly ShellConfiguration _configuration;
    private Process? _process;

    internal ModelSetupSession(ShellConfiguration configuration)
    {
        _configuration = configuration;
    }

    internal async Task<ModelSetupResult> PrepareAsync(
        Action<ModelSetupProgress> progress)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = _configuration.CoordinatorPath,
            WorkingDirectory =
                _configuration.CoordinatorWorkingDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = new UTF8Encoding(false),
            StandardErrorEncoding = new UTF8Encoding(false),
        };
        foreach (var argument in new[]
        {
            "-m",
            "totalsegmentator_wrapper_mac.totalseg_model_setup",
            "--manifest",
            _configuration.TotalSegmentatorModelManifestPath,
            "--model-root",
            _configuration.TotalSegmentatorHome,
        })
        {
            startInfo.ArgumentList.Add(argument);
        }
        startInfo.Environment["PYTHONUTF8"] = "1";
        startInfo.Environment["PYTHONIOENCODING"] = "utf-8";
        try
        {
            _process = Process.Start(startInfo)
                ?? throw new InvalidOperationException();
            var stderrDrain = _process.StandardError.ReadToEndAsync();
            ModelSetupResult? terminal = null;
            while (await _process.StandardOutput.ReadLineAsync()
                is { } line)
            {
                if (line.StartsWith(
                    ProgressPrefix,
                    StringComparison.Ordinal))
                {
                    var parsed = JsonSerializer.Deserialize<ModelSetupProgress>(
                        line[ProgressPrefix.Length..]);
                    if (parsed is not null)
                    {
                        progress(parsed);
                    }
                    continue;
                }
                try
                {
                    terminal = JsonSerializer.Deserialize<ModelSetupResult>(
                        line);
                }
                catch (JsonException)
                {
                    // Third-party or unexpected output is never forwarded.
                }
            }
            await _process.WaitForExitAsync();
            await stderrDrain;
            return _process.ExitCode == 0
                && terminal?.Status == "success"
                && terminal.FallbackAllowed == false
                    ? terminal
                    : terminal ?? ModelSetupResult.Failure(
                        "model_prepare_failed",
                        "モデルの準備を完了できませんでした。");
        }
        catch (Exception exception) when (
            exception is IOException
                or InvalidOperationException
                or JsonException)
        {
            return ModelSetupResult.Failure(
                "model_prepare_unavailable",
                "モデル準備機能を開始できませんでした。");
        }
    }

    internal static bool ContractSelfTest()
    {
        var progress = JsonSerializer.Deserialize<ModelSetupProgress>(
            "{\"stage\":\"download\",\"status\":\"running\","
            + "\"message\":\"safe\",\"percent\":42,"
            + "\"downloaded_bytes\":42,\"total_bytes\":100,"
            + "\"rate_bps\":10.0,\"eta_seconds\":5.8,"
            + "\"resumed\":true}");
        var result = JsonSerializer.Deserialize<ModelSetupResult>(
            "{\"status\":\"success\",\"model_state\":\"ready\","
            + "\"sha256_verified\":true,\"fallback_allowed\":false,"
            + "\"error_code\":null,\"safe_reason\":null}");
        return progress is
            {
                Stage: "download",
                Percent: 42,
                Resumed: true,
            }
            && result is
            {
                Status: "success",
                ModelState: "ready",
                Sha256Verified: true,
                FallbackAllowed: false,
            };
    }

    public void Dispose()
    {
        if (_process is { HasExited: false })
        {
            _process.Kill(entireProcessTree: true);
        }
        _process?.Dispose();
        _process = null;
    }
}

internal sealed record ModelSetupProgress(
    [property: JsonPropertyName("stage")] string Stage,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("message")] string Message,
    [property: JsonPropertyName("percent")] int? Percent,
    [property: JsonPropertyName("downloaded_bytes")] long? DownloadedBytes,
    [property: JsonPropertyName("total_bytes")] long? TotalBytes,
    [property: JsonPropertyName("rate_bps")] double? RateBps,
    [property: JsonPropertyName("eta_seconds")] double? EtaSeconds,
    [property: JsonPropertyName("resumed")] bool? Resumed);

internal sealed record ModelSetupResult(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("model_state")] string? ModelState,
    [property: JsonPropertyName("sha256_verified")] bool? Sha256Verified,
    [property: JsonPropertyName("fallback_allowed")] bool? FallbackAllowed,
    [property: JsonPropertyName("error_code")] string? ErrorCode,
    [property: JsonPropertyName("safe_reason")] string? SafeReason)
{
    internal static ModelSetupResult Failure(
        string errorCode,
        string safeReason) =>
        new(
            "failed",
            null,
            false,
            false,
            errorCode,
            safeReason);
}
