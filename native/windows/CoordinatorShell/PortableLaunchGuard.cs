using System.IO;

namespace TotalSegmentatorWrapper.Windows.CoordinatorShell;

internal static class PortableLaunchGuard
{
    internal static bool IsArchiveDirectLaunch(
        string baseDirectory,
        string temporaryDirectory)
    {
        try
        {
            var basePath = Path.GetFullPath(baseDirectory);
            var tempPath = Path.GetFullPath(temporaryDirectory);
            var relative = Path.GetRelativePath(tempPath, basePath);
            if (relative == "."
                || relative == ".."
                || relative.StartsWith(
                    $"..{Path.DirectorySeparatorChar}",
                    StringComparison.Ordinal))
            {
                return false;
            }

            return relative
                .Split(
                    Path.DirectorySeparatorChar,
                    StringSplitOptions.RemoveEmptyEntries)
                .Any(
                    segment =>
                        segment.StartsWith(
                            "Temp",
                            StringComparison.OrdinalIgnoreCase)
                        && segment.Contains(
                            ".zip",
                            StringComparison.OrdinalIgnoreCase));
        }
        catch (Exception exception) when (
            exception is ArgumentException
                or IOException
                or NotSupportedException)
        {
            return false;
        }
    }

    internal static bool ContractSelfTest()
    {
        const string temp = @"C:\Users\tester\AppData\Local\Temp";
        return IsArchiveDirectLaunch(
                temp
                    + @"\Temp1_TotalSegmentatorWrapperForWin-Alpha.zip"
                    + @"\TotalSegmentatorWrapperForWin",
                temp)
            && !IsArchiveDirectLaunch(
                @"C:\Portable\TotalSegmentatorWrapperForWin",
                temp)
            && !IsArchiveDirectLaunch(
                temp + @"\explicitly-extracted\TotalSegmentatorWrapperForWin",
                temp);
    }
}
