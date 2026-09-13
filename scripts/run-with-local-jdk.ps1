param(
    [string]$MvnArgs = "-DskipTests spring-boot:run"
)

# Determine project root relative to scripts folder
$projectRoot = Resolve-Path "$PSScriptRoot\.."
$jdkDir = Join-Path $projectRoot "jdk"
if (-Not (Test-Path $jdkDir)) {
    Write-Error "Local JDK not found at $jdkDir. Run .\scripts\install-jdk.ps1 first."
    exit 1
}

# Find the extracted JDK folder (some archives include a nested folder name like jdk-17...)
$jdkRoot = Get-ChildItem $jdkDir | Where-Object { $_.PSIsContainer } | Select-Object -First 1
if ($null -eq $jdkRoot) {
    $jdkRoot = Get-Item $jdkDir
}

$absJdkPath = $jdkRoot.FullName
Write-Output "Using local JDK at $absJdkPath"

$env:JAVA_HOME = $absJdkPath
$env:Path = "$env:JAVA_HOME\bin;$env:Path"

Push-Location (Join-Path $projectRoot "facerecognition")
try {
    if (Test-Path "mvnw.cmd") {
        & .\mvnw.cmd $MvnArgs
    } else {
        Write-Error "mvnw.cmd not found in facerecognition. Ensure the project has the Maven wrapper."
        exit 1
    }
} finally {
    Pop-Location
}
