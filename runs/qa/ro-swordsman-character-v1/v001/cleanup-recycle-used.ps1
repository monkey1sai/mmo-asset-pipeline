# Move the files listed in cleanup-list-01.txt to the Recycle Bin (recoverable; nothing is hard-deleted).
param([string]$List)
Add-Type -AssemblyName Microsoft.VisualBasic
$root = 'C:\Repos\mmo-asset-pipeline\tmp\art-quality-loop\assets\processed\ro-swordsman-character-v1\v001\'
$moved = 0
foreach ($path in Get-Content -LiteralPath $List -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($path)) { continue }
    if (-not $path.StartsWith($root) -or -not $path.EndsWith('.blend') -or $path.EndsWith('b03-hands\ro_character_v001_b03-hands.blend')) { throw "REFUSED $path" }
    if (Test-Path -LiteralPath $path) {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($path, 'OnlyErrorDialogs', 'SendToRecycleBin')
        $moved++
    }
}
Write-Output "moved_to_recycle_bin=$moved"
