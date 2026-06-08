$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

$python = $null
try {
  py -3.14 --version | Out-Null
  $python = "py -3.14"
} catch {
  try {
    py --version | Out-Null
    $python = "py"
  } catch {
    python --version | Out-Null
    $python = "python"
  }
}

Write-Host "Building desktop package..."
$appName = "i dont know less than you"
Invoke-Expression "$python -m PyInstaller --noconfirm --onefile --noconsole --name `"$appName`" app.py"

$packageDir = Join-Path $PSScriptRoot "dist\i dont know less than you"
New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "dist\i dont know less than you.exe") -Destination $packageDir -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "index.html") -Destination $packageDir -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "config.yaml") -Destination $packageDir -Force
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot "title.gif")) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot "title.gif") -Destination $packageDir -Force
} else {
  Write-Warning "title.gif was not found. Put title.gif beside app.py before building if you want the title GIF included."
}

Write-Host ""
Write-Host "Done:"
Write-Host $packageDir
