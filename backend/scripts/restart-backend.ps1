# Stop duplicate API listeners on port 8000, then start one backend.
$ErrorActionPreference = "SilentlyContinue"
$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique
foreach ($pid in $listeners) {
  if ($pid -gt 0) { Stop-Process -Id $pid -Force }
}
Start-Sleep -Seconds 2

Set-Location $PSScriptRoot\..
& .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
