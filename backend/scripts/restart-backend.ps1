# Use port 8010 so stale zombies on 8000 are ignored.
$Port = 8010
$ErrorActionPreference = "SilentlyContinue"

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique
foreach ($pid in $listeners) {
  if ($pid -gt 0) { Stop-Process -Id $pid -Force }
}
Start-Sleep -Seconds 2

Set-Location $PSScriptRoot\..
$env:TALENTDESK_PRIMARY_API = "1"
& .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port $Port
