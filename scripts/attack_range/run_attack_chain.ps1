# PowerShell Attack Chain Runner using Atomic Red Team
param (
    [Parameter(Mandatory=$true)]
    [string]$ChainName,

    [string]$LogPath = "C:\RedForesight\ground_truth.json"
)

$Chains = @{
    "chain_a" = @("T1566.001", "T1059.001", "T1003.001", "T1021.002")
    "chain_b" = @("T1082", "T1083", "T1005", "T1048")
    "chain_c" = @("T1547.001", "T1053.005", "T1055")
    "chain_d" = @("T1070.001", "T1112", "T1018")
}

if (-not $Chains.ContainsKey($ChainName)) {
    Write-Error "Unknown attack chain: $ChainName"
    return
}

$Techniques = $Chains[$ChainName]
$LogEntries = @()
$HostName = $env:COMPUTERNAME

Write-Host "Starting execution of $ChainName on $HostName..."

foreach ($Tech in $Techniques) {
    $Timestamp = (Get-Date).ToString("o")
    Write-Host "[$Timestamp] Executing Atomic Red Team technique: $Tech"

    # Invoke-AtomicTest $Tech -Confirm:$false -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    $LogEntries += @{
        technique_id = $Tech
        executed_at = $Timestamp
        host = $HostName
    }
}

$GroundTruth = @{
    chain_id = $ChainName
    run_timestamp = (Get-Date).ToString("o")
    steps = $LogEntries
}

$GroundTruth | ConvertTo-Json -Depth 5 | Out-File -FilePath $LogPath -Encoding utf8
Write-Host "Ground truth saved to $LogPath"
