param([string]$Q="", [string]$F="")

if(!$Q){
    $Q = Read-Host "Search for game"
    if($F -and !$F){$F = Read-Host "Filter (e.g. InsaneRamZes, FitGirl) or Enter to skip"}
}
if(!$Q){exit}

$url="https://rutor.info/search/0/0/000/0/$([System.Uri]::EscapeDataString($Q))"
try{$r=Invoke-WebRequest -Uri $url -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -TimeoutSec 20 -UseBasicParsing;$h=$r.Content}catch{Write-Host "Error: $_";exit}

$i=0
$results=[regex]::Matches($h,'<tr class="(?:gai|tum)">(.*?)</tr>',[System.Text.RegularExpressions.RegexOptions]::Singleline)|%{
    $row=$_.Groups[1].Value
    $t=[regex]::Match($row,'href="/torrent/\d+/[^"]*">(.*?)</a>').Groups[1].Value
    $m=[regex]::Match($row,'href="(magnet:\?[^"]+)"').Groups[1].Value
    if(!$m){continue}
    # Filter
    if($F -and $t -notlike "*$F*"){return} # skip - return continues to next item in pipeline
    $s=[regex]::Match($row,'([\d.]+)\s*(?:&nbsp;)?\s*(GB|MB|KB)')
    $z=if($s.Success){"$($s.Groups[1].Value) $($s.Groups[2].Value)"}else{""}
    $k=[regex]::Match($row,'arrowup.*?>\s*(\d+)')
    $d=if($k.Success){[int]$k.Groups[1].Value}else{0}
    [PSCustomObject]@{Title=[System.Net.WebUtility]::HtmlDecode($t);Size=$z;Seeds=$d;Magnet=$m}
}|Sort Seeds -Descending

if($results.Count-eq0){Write-Host "No results.";exit}

$results|%{$i++;$n="[$(([string]$i).PadLeft(2))]"
    Write-Host "$n $($_.Title)"
    Write-Host "    Size: $($_.Size.PadLeft(10)) | Seeds: $($_.Seeds)"
    Write-Host ""
}

$c=-1
while($c-lt0-or$c-ge$results.Count){
    $x=Read-Host "Pick (1-$($results.Count)) or q"
    if($x-eq'q'){exit}
    if([int]::TryParse($x,[ref]$c)){$c-=1}
}

Write-Host "Opening in qBittorrent: $($results[$c].Title)"
Start-Process $results[$c].Magnet
Write-Host "Done!"
