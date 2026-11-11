param([Parameter(Mandatory=$true)][string]$ComfyRoot)
$ErrorActionPreference = 'Stop'
$source = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\sprite_studio'))
$root = (Resolve-Path -LiteralPath $ComfyRoot).Path
$destination = [IO.Path]::GetFullPath((Join-Path $root 'custom_nodes\mumblebox_sprite_studio'))
if ($source -match '(?i)OneDrive' -or $destination -match '(?i)OneDrive') { throw 'Sprite Studio installs require a plain local directory.' }
if (-not (Test-Path -LiteralPath (Join-Path $root 'main.py'))) { throw 'Select an existing ComfyUI installation.' }
if (-not $destination.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid install destination.' }
$stageRoot = [IO.Path]::GetFullPath((Join-Path $root ('user\mumblebox_sprite_studio\install_staging\' + [guid]::NewGuid().ToString('N'))))
if (-not $stageRoot.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid staging destination.' }
New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
$stagedPackage = Join-Path $stageRoot 'package'
$files = Get-ChildItem -LiteralPath $source -Recurse -File | Where-Object { $_.FullName -notmatch '\\__pycache__\\' }
New-Item -ItemType Directory -Path $stagedPackage -Force | Out-Null
foreach ($file in $files) {
    $relative = [IO.Path]::GetRelativePath($source, $file.FullName)
    $stagedFile = Join-Path $stagedPackage $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $stagedFile) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $stagedFile
}
foreach ($file in $files) {
    $relative = [IO.Path]::GetRelativePath($source, $file.FullName)
    if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath (Join-Path $stagedPackage $relative) -Algorithm SHA256).Hash) { throw "Staged file mismatch: $relative. Existing install remains unchanged." }
}
$backup = $null
if (Test-Path -LiteralPath $destination) {
    $backupRoot = Join-Path $root 'user\mumblebox_sprite_studio\install_backups'
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    $backup = Join-Path $backupRoot ([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-ffff'))
    if (-not ([IO.Path]::GetFullPath($backup)).StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid backup destination.' }
    Move-Item -LiteralPath $destination -Destination $backup
    Write-Output "Previous package preserved: $backup"
}
try {
    Move-Item -LiteralPath $stagedPackage -Destination $destination
} catch {
    if ($backup -and -not (Test-Path -LiteralPath $destination)) { Move-Item -LiteralPath $backup -Destination $destination }
    throw
}
foreach ($file in $files) {
    $relative = [IO.Path]::GetRelativePath($source, $file.FullName)
    $installed = Join-Path $destination $relative
    if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash) { throw "Installed file mismatch: $relative" }
}
Write-Output "Verified $($files.Count) files in $destination. Restart the existing Desktop installation to load Python changes."
