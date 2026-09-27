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

# Determine the actual JDK root
$jdkRoot = Get-Item $jdkDir
if (-Not (Test-Path (Join-Path $jdkRoot.FullName "bin\java.exe"))) {
    $nested = Get-ChildItem $jdkDir | Where-Object { $_.PSIsContainer -and (Test-Path (Join-Path $_.FullName "bin\java.exe")) } | Select-Object -First 1
    if ($null -ne $nested) {
        $jdkRoot = $nested
    } else {
        Write-Error "Could not find bin\java.exe in local JDK directory."
        exit 1
    }
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
