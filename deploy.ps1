<#
.SYNOPSIS
    Build/convert and deploy the Kerbal Space Neco Arc mod into KSP.

.DESCRIPTION
    Regenerates the Neco Arc head from the OBJ, (optionally) rebuilds the C#
    plugin, and copies the results into the KSP GameData install.

    Run from the repo root:  .\deploy.ps1
    Common uses:
        .\deploy.ps1                # convert model + copy models/textures (fast, for scale tuning)
        .\deploy.ps1 -Height 0.45   # convert at a bigger head scale, then deploy
        .\deploy.ps1 -Reduction 0.4 # keep more detail (remove only 40% of tris), then deploy
        .\deploy.ps1 -OffsetY 0.6   # raise the head (e.g. off the feet), then deploy
        .\deploy.ps1 -Dll           # also rebuild + copy the C# plugin DLL
        .\deploy.ps1 -Dll -SkipConvert   # only rebuild/copy the DLL

.NOTES
    After deploying, restart KSP - it only reads models/plugins at load time.
#>
[CmdletBinding()]
param(
    # Rebuild and deploy the C# plugin DLL as well as the assets.
    [switch]$Dll,

    # Skip running the Python model converter (use existing staged assets).
    [switch]$SkipConvert,

    # Override the head scale (y-extent in KSP mesh units). Default in the
    # converter is 0.35. Passed to the converter via NECO_TARGET_HEIGHT.
    [double]$Height,

    # Override the decimation amount (fraction of triangles removed, 0..1).
    # Default in the converter is 0.6 (keep 40%); lower keeps more detail.
    # Passed to the converter via NECO_TARGET_REDUCTION.
    [double]$Reduction,

    # Shift the head position in final KSP mesh units (same scale as -Height).
    # +Y raises the head, +Z pushes it forward, +X moves it right.
    [double]$OffsetX,
    [double]$OffsetY,
    [double]$OffsetZ,

    # KSP install root (override if it ever moves).
    [string]$KspRoot = "E:\Node 1\SteamLibrary\steamapps\common\Kerbal Space Program"
)

$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot

$modName   = 'KerbalSpaceNecoArc'
$staged    = Join-Path $repo "GameData\$modName"
$destMod   = Join-Path $KspRoot "GameData\$modName"
$csproj    = Join-Path $repo "$modName\$modName.csproj"
$builtDll  = Join-Path $repo "$modName\bin\Debug\net471\$modName.dll"
$converter = Join-Path $repo 'ModelConverter\neco_convert.py'

if (-not (Test-Path $KspRoot)) {
    throw "KSP install not found at: $KspRoot  (pass -KspRoot '...')"
}

# 1. Convert the OBJ -> KSP mesh + texture (staged under repo GameData).
if (-not $SkipConvert) {
    Write-Host '== Converting model ==' -ForegroundColor Cyan
    if ($PSBoundParameters.ContainsKey('Height')) {
        Write-Host "   head scale (TARGET_HEIGHT) = $Height" -ForegroundColor DarkCyan
        $env:NECO_TARGET_HEIGHT = $Height
    }
    if ($PSBoundParameters.ContainsKey('Reduction')) {
        Write-Host "   decimation (TARGET_REDUCTION) = $Reduction" -ForegroundColor DarkCyan
        $env:NECO_TARGET_REDUCTION = $Reduction
    }
    if ($PSBoundParameters.ContainsKey('OffsetX')) { $env:NECO_OFFSET_X = $OffsetX }
    if ($PSBoundParameters.ContainsKey('OffsetY')) { $env:NECO_OFFSET_Y = $OffsetY }
    if ($PSBoundParameters.ContainsKey('OffsetZ')) { $env:NECO_OFFSET_Z = $OffsetZ }
    if ($PSBoundParameters.ContainsKey('OffsetX') -or
        $PSBoundParameters.ContainsKey('OffsetY') -or
        $PSBoundParameters.ContainsKey('OffsetZ')) {
        Write-Host "   head offset (x,y,z) = ($OffsetX,$OffsetY,$OffsetZ)" -ForegroundColor DarkCyan
    }
    Push-Location (Split-Path $converter)
    try { python (Split-Path $converter -Leaf) }
    finally {
        Pop-Location
        Remove-Item Env:NECO_TARGET_HEIGHT -ErrorAction SilentlyContinue
        Remove-Item Env:NECO_TARGET_REDUCTION -ErrorAction SilentlyContinue
        Remove-Item Env:NECO_OFFSET_X -ErrorAction SilentlyContinue
        Remove-Item Env:NECO_OFFSET_Y -ErrorAction SilentlyContinue
        Remove-Item Env:NECO_OFFSET_Z -ErrorAction SilentlyContinue
    }
}
elseif ($PSBoundParameters.ContainsKey('Height') -or
        $PSBoundParameters.ContainsKey('Reduction') -or
        $PSBoundParameters.ContainsKey('OffsetX') -or
        $PSBoundParameters.ContainsKey('OffsetY') -or
        $PSBoundParameters.ContainsKey('OffsetZ')) {
    Write-Warning '-Height/-Reduction/-Offset* are ignored together with -SkipConvert (no conversion runs).'
}

# 2. Optionally rebuild the plugin DLL.
if ($Dll) {
    Write-Host '== Building plugin ==' -ForegroundColor Cyan
    dotnet build $csproj -c Debug -p:KSPRoot="$KspRoot" /consoleloggerparameters:NoSummary
    if ($LASTEXITCODE -ne 0) { throw 'dotnet build failed.' }
}

# 3. Copy staged assets into the KSP install.
Write-Host '== Deploying to KSP ==' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path (Join-Path $destMod 'Plugins') | Out-Null
Copy-Item (Join-Path $staged 'Models')   $destMod -Recurse -Force
Copy-Item (Join-Path $staged 'Textures') $destMod -Recurse -Force
if ($Dll) {
    Copy-Item $builtDll (Join-Path $destMod 'Plugins') -Force
}

# 4. Report what is now installed.
Write-Host '== Installed files ==' -ForegroundColor Green
Get-ChildItem -Recurse -File $destMod | ForEach-Object {
    '{0,-8} {1}' -f ([math]::Round($_.Length / 1KB, 1).ToString() + 'KB'),
        $_.FullName.Substring($_.FullName.IndexOf('GameData'))
}
Write-Host "`nDone. Restart KSP to load the changes." -ForegroundColor Green
