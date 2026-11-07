<#
HW6 Part B, Power BI side - export the measure values from the OPEN hw06.pbix.

Runs the DAX queries in powerbi/export_queries.dax against the model that
Power BI Desktop has open (the same engine DAX query view uses), and writes
reports/powerbi_values.csv in the long format measure, slice, value.
Values are written unrounded (round-trip "R" format), so the reconciliation
can test them to the cent.

Also writes reports/powerbi_part_c.csv (the Power BI side of Part C (a)).

Run in Windows PowerShell with hw06.pbix open in Power BI Desktop:
    powershell -ExecutionPolicy Bypass -File hw06/scripts/02_export_powerbi_values.ps1
#>
$ErrorActionPreference = "Stop"
$hw = Split-Path -Parent $PSScriptRoot
$bin = "C:\Program Files\Microsoft Power BI Desktop\bin"
Add-Type -Path "$bin\Microsoft.PowerBI.AdomdClient.dll"

# The local Analysis Services instance behind Power BI Desktop writes its port here
$portFile = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces" -Recurse -Filter msmdsrv.port.txt |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $portFile) { throw "Power BI Desktop is not running with a model open." }
$port = [System.Text.Encoding]::Unicode.GetString([IO.File]::ReadAllBytes($portFile.FullName)).Trim([char]0, ' ')

$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$port")
$conn.Open()
$inv = [Globalization.CultureInfo]::InvariantCulture

function Run([string]$dax) {
    $cmd = $conn.CreateCommand(); $cmd.CommandText = $dax
    $r = $cmd.ExecuteReader(); $rows = @()
    while ($r.Read()) {
        $o = [ordered]@{}
        for ($i = 0; $i -lt $r.FieldCount; $i++) { $o[$r.GetName($i)] = $r.GetValue($i) }
        $rows += [pscustomobject]$o
    }
    $r.Close(); return $rows
}

# ADOMD names a ROW/SUMMARIZECOLUMNS result column "[name]": remove exactly one outer pair,
# so a name that itself ends in "]" (e.g. "... [Ending AUM]") keeps its own bracket
function Strip([string]$n) { if ($n -match '^\[(.*)\]$') { return $Matches[1] } return $n }

function Fmt($v) {
    if ($v -is [DBNull] -or $null -eq $v) { return "" }
    if ($v -is [double]) { return $v.ToString("R", $inv) }
    if ($v -is [decimal] -or $v -is [long] -or $v -is [int]) { return $v.ToString($inv) }
    return [string]$v
}

# The newest port file belongs to the most recently opened Power BI window. Make sure it
# is hw06.pbix (17 measures in _Measures), not another report that happens to be open.
$check = Run 'EVALUATE ROW ( "n", COUNTROWS ( FILTER ( INFO.VIEW.MEASURES (), [Table] = "_Measures" ) ) )'
if ($check[0].'[n]' -ne 17) { throw "Connected model has $($check[0].'[n]') _Measures measures, expected 17: is hw06.pbix the last Power BI file opened?" }

# Queries are kept in a .dax file so they can be pasted into DAX query view unchanged.
# Each block starts with a line "-- slice: <label or column>".
$text = Get-Content (Join-Path $hw "powerbi\export_queries.dax") -Raw -Encoding UTF8
# The text before the first "-- slice:" line is the file's header comment, not a query
$blocks = [regex]::Split($text, "(?m)^-- slice: ") | Select-Object -Skip 1

$out = New-Object System.Collections.Generic.List[object]
foreach ($b in $blocks) {
    $nl = $b.IndexOf("`n")
    $spec = $b.Substring(0, $nl).Trim(); $dax = $b.Substring($nl + 1)
    # spec is either a fixed label ("All") or "col=<group-by column>;label=<template with {}>"
    foreach ($row in (Run $dax)) {
        $names = $row.PSObject.Properties.Name
        if ($spec -like "col=*") {
            $parts = @{}; $spec.Split(";") | ForEach-Object { $k, $v = $_.Split("=", 2); $parts[$k] = $v }
            $key = $names | Where-Object { $_ -like "*[[]$($parts.col)]" } | Select-Object -First 1
            $label = $parts.label.Replace("{}", (Fmt $row.$key))
        } else { $key = $null; $label = $spec }
        foreach ($n in $names) {
            if ($n -eq $key) { continue }
            $out.Add([pscustomobject]@{ measure = (Strip $n); slice = $label; value = Fmt $row.$n })
        }
    }
}
$csv = Join-Path $hw "reports\powerbi_values.csv"
$out | Export-Csv $csv -NoTypeInformation -Encoding UTF8
"wrote $($out.Count) values -> $csv"

# Part C (a): Ending AUM vs SUMX over clients, both from Power BI
$pc = Run @"
EVALUATE
ROW (
    "Ending AUM", [Ending AUM],
    "SUMX over clients of [Ending AUM]", SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )
)
"@
$pcRows = foreach ($n in $pc[0].PSObject.Properties.Name) { [pscustomobject]@{ figure = (Strip $n); value = Fmt $pc[0].$n } }
$pcFile = Join-Path $hw "reports\powerbi_part_c.csv"
$pcRows | Export-Csv $pcFile -NoTypeInformation -Encoding UTF8
"wrote Part C (a) -> $pcFile"
$conn.Close()
