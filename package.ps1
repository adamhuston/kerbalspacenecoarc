<#
.SYNOPSIS
    Build the plugin and package a clean release zip for CKAN / manual install.

.DESCRIPTION
    Produces dist/KerbalSpaceNecoArc-<version>.zip containing ONLY
    GameData/KerbalSpaceNecoArc (Models, Textures, the .version file, and
    Plugins/KerbalSpaceNecoArc.dll) - exactly what CKAN installs. No source,
    converter, or dev assets are included.

    Set the KSPDIR environment variable (or pass -KspRoot) so the build can
    reference the stock KSP managed assemblies.

    Usage:
        $env:KSPDIR = 'C:\...\Kerbal Space Program'
        .\package.ps1
    Upload the resulting dist\*.zip as the GitHub Release asset CKAN points at.
#>
[CmdletBinding()]
param(
    # KSP install root, used only to reference stock assemblies at build time.
    [string]$KspRoot = $env:KSPDIR,

    [ValidateSet('Release', 'Debug')]
    [string]$Configuration = 'Release'
)

$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$modName = 'KerbalSpaceNecoArc'
$csproj = Join-Path $repo "$modName\$modName.csproj"
$gameData = Join-Path $repo "GameData\$modName"
$versionFile = Join-Path $gameData "$modName.version"

if (-not $KspRoot) {
    throw "KSP install not set. Set the KSPDIR environment variable or pass -KspRoot '<KSP install folder>'."
}

# Version string from the KSP-AVC .version file.
$v = (Get-Content $versionFile -Raw | ConvertFrom-Json).VERSION
$version = "$($v.MAJOR).$($v.MINOR).$($v.PATCH)"

# 1. Build the plugin.
Write-Host "== Building $modName ($Configuration) ==" -ForegroundColor Cyan
dotnet build $csproj -c $Configuration -p:KSPRoot="$KspRoot" /consoleloggerparameters:NoSummary
if ($LASTEXITCODE -ne 0) { throw 'dotnet build failed.' }
$dll = Join-Path $repo "$modName\bin\$Configuration\net471\$modName.dll"
if (-not (Test-Path $dll)) { throw "Built DLL not found: $dll" }

# 2. Stage a clean GameData tree.
$dist = Join-Path $repo 'dist'
$stage = Join-Path $dist 'stage'
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
$stageMod = Join-Path $stage "GameData\$modName"
New-Item -ItemType Directory -Force -Path (Join-Path $stageMod 'Plugins') | Out-Null
Copy-Item (Join-Path $gameData 'Models')   $stageMod -Recurse -Force
Copy-Item (Join-Path $gameData 'Textures') $stageMod -Recurse -Force
Copy-Item $versionFile $stageMod -Force
Copy-Item $dll (Join-Path $stageMod 'Plugins') -Force

# 3. Zip it (archive root contains GameData/KerbalSpaceNecoArc/...).
New-Item -ItemType Directory -Force -Path $dist | Out-Null
$zip = Join-Path $dist "$modName-$version.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path (Join-Path $stage 'GameData') -DestinationPath $zip
Remove-Item -Recurse -Force $stage

# 4. Report contents.
Write-Host "`n== Packaged $zip ==" -ForegroundColor Green
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
try { $archive.Entries | ForEach-Object { '  ' + $_.FullName } }
finally { $archive.Dispose() }
Write-Host "`nUpload this zip as the GitHub Release asset." -ForegroundColor Green
