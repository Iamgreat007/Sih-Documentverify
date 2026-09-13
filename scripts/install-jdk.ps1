param(
    [string]$InstallDir = "${PSScriptRoot}\..\jdk"
)

$zipUrl = "https://github.com/adoptium/temurin17-binaries/releases/latest/download/OpenJDK17U-jdk_x64_windows_hotspot.zip"
$zipPath = Join-Path $env:TEMP "jdk17.zip"
$extractTemp = Join-Path $env:TEMP "jdk-extract"

Write-Output "Downloading JDK 17 from $zipUrl..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing

if (Test-Path $extractTemp) { Remove-Item $extractTemp -Recurse -Force }
Expand-Archive -Path $zipPath -DestinationPath $extractTemp -Force

# Move the extracted JDK folder into the project-local jdk directory
$extracted = Get-ChildItem $extractTemp | Where-Object { $_.PSIsContainer } | Select-Object -First 1
if ($null -eq $extracted) { Throw "Failed to extract JDK archive" }

$targetDir = Resolve-Path -LiteralPath $InstallDir -ErrorAction SilentlyContinue
if ($targetDir) { Remove-Item $targetDir -Recurse -Force }

Move-Item -Path $extracted.FullName -Destination $InstallDir

# Clean up
Remove-Item $zipPath -Force
Remove-Item $extractTemp -Recurse -Force

Write-Output "JDK installed to $InstallDir"
Write-Output "To use it for running the app locally run: .\scripts\run-with-local-jdk.ps1"
