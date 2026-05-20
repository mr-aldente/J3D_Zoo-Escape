# Split raccoon spritesheet into per-frame PNGs (Fox-style tight crops).
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

function Test-SpritePixel([System.Drawing.Color]$c) {
    if ($c.A -lt 8) { return $false }
    if ($c.R -lt 18 -and $c.G -lt 18 -and $c.B -lt 18) { return $false }
    return $true
}

function Get-ContentBounds([System.Drawing.Bitmap]$bmp, [int]$x0, [int]$y0, [int]$w, [int]$h, [int]$margin = 6) {
    $minX = $bmp.Width; $minY = $bmp.Height
    $maxX = -1; $maxY = -1
    $x1 = [Math]::Min($bmp.Width, $x0 + $w) - 1
    $y1 = [Math]::Min($bmp.Height, $y0 + $h) - 1
    for ($y = $y0; $y -le $y1; $y++) {
        for ($x = $x0; $x -le $x1; $x++) {
            if (Test-SpritePixel $bmp.GetPixel($x, $y)) {
                if ($x -lt $minX) { $minX = $x }
                if ($y -lt $minY) { $minY = $y }
                if ($x -gt $maxX) { $maxX = $x }
                if ($y -gt $maxY) { $maxY = $y }
            }
        }
    }
    if ($maxX -lt $minX) { return $null }
    $minX = [Math]::Max(0, $minX - $margin)
    $minY = [Math]::Max(0, $minY - $margin)
    $maxX = [Math]::Min($bmp.Width - 1, $maxX + $margin)
    $maxY = [Math]::Min($bmp.Height - 1, $maxY + $margin)
    return [PSCustomObject]@{
        X = $minX; Y = $minY
        W = ($maxX - $minX + 1); H = ($maxY - $minY + 1)
    }
}

function Get-RowBands([System.Drawing.Bitmap]$bmp) {
    $counts = New-Object int[] $bmp.Height
    for ($y = 0; $y -lt $bmp.Height; $y++) {
        $n = 0
        for ($x = 0; $x -lt $bmp.Width; $x++) {
            if (Test-SpritePixel $bmp.GetPixel($x, $y)) { $n++ }
        }
        $counts[$y] = $n
    }
    $bands = @()
    $inBand = $false
    $start = 0
    for ($y = 0; $y -lt $bmp.Height; $y++) {
        if ($counts[$y] -gt 12) {
            if (-not $inBand) { $start = $y; $inBand = $true }
        } elseif ($inBand) {
            $bands += [PSCustomObject]@{ Y = $start; H = ($y - $start) }
            $inBand = $false
        }
    }
    if ($inBand) {
        $bands += [PSCustomObject]@{ Y = $start; H = ($bmp.Height - $start) }
    }
    return $bands
}

function Get-ColumnCounts([System.Drawing.Bitmap]$bmp, [int]$y0, [int]$h) {
    $counts = New-Object int[] $bmp.Width
    for ($x = 0; $x -lt $bmp.Width; $x++) {
        $n = 0
        for ($y = $y0; $y -lt ($y0 + $h); $y++) {
            if (Test-SpritePixel $bmp.GetPixel($x, $y)) { $n++ }
        }
        $counts[$x] = $n
    }
    return $counts
}

function Get-GapRegions([int[]]$counts, [int]$threshold = 4, [int]$minGapWidth = 6) {
    $regions = @()
    $inGap = $false
    $gapStart = 0
    for ($x = 0; $x -lt $counts.Length; $x++) {
        if ($counts[$x] -le $threshold) {
            if (-not $inGap) { $gapStart = $x; $inGap = $true }
        } elseif ($inGap) {
            $gapEnd = $x - 1
            $width = $gapEnd - $gapStart + 1
            if ($width -ge $minGapWidth) {
                $regions += [PSCustomObject]@{
                    Start = $gapStart
                    End   = $gapEnd
                    Width = $width
                    Mid   = [int](($gapStart + $gapEnd) / 2)
                }
            }
            $inGap = $false
        }
    }
    return $regions
}

function Get-ColumnSlices([System.Drawing.Bitmap]$bmp, [int]$y0, [int]$h, [int]$frameCount) {
    $counts = Get-ColumnCounts $bmp $y0 $h
    $rowBounds = Get-ContentBounds $bmp 0 $y0 $bmp.Width $h 0
    if ($null -eq $rowBounds) { return @() }

    $contentStart = $rowBounds.X
    $contentEnd = $rowBounds.X + $rowBounds.W - 1
    $gapRegions = @(
        Get-GapRegions $counts |
        Where-Object { $_.Mid -gt ($contentStart + 12) -and $_.Mid -lt ($contentEnd - 12) }
    )

    $neededGaps = $frameCount - 1
    if ($gapRegions.Count -ge $neededGaps) {
        $picked = @(
            $gapRegions |
            Sort-Object { $_.Width } -Descending |
            Select-Object -First $neededGaps |
            Sort-Object { $_.Mid }
        )
        $cuts = @($contentStart)
        foreach ($gap in $picked) {
            $cuts += ($gap.End + 1)
        }
        $cuts += ($contentEnd + 1)

        $slices = @()
        for ($i = 0; $i -lt $frameCount; $i++) {
            $x0 = [int]$cuts[$i]
            $x1 = [int]$cuts[$i + 1]
            if ($x1 -gt $x0) {
                $slices += [PSCustomObject]@{ X = $x0; W = ($x1 - $x0) }
            }
        }
        if ($slices.Count -eq $frameCount) { return $slices }
    }

    # Fallback: equal-width cells
    $span = $contentEnd - $contentStart + 1
    $cell = $span / [double]$frameCount
    $slices = @()
    for ($i = 0; $i -lt $frameCount; $i++) {
        $x0 = [int][math]::Round($contentStart + $i * $cell)
        $x1 = [int][math]::Round($contentStart + ($i + 1) * $cell)
        if ($x1 -le $x0) { $x1 = $x0 + 1 }
        $slices += [PSCustomObject]@{ X = $x0; W = ($x1 - $x0) }
    }
    return $slices
}

function Get-ConnectedComponents([System.Drawing.Bitmap]$bmp) {
    $w = $bmp.Width
    $h = $bmp.Height
    $visited = New-Object bool[] ($w * $h)
    $components = @()
    $dirs = @((1, 0), (-1, 0), (0, 1), (0, -1))

    for ($y = 0; $y -lt $h; $y++) {
        for ($x = 0; $x -lt $w; $x++) {
            $idx = $y * $w + $x
            if ($visited[$idx]) { continue }
            if (-not (Test-SpritePixel $bmp.GetPixel($x, $y))) { continue }

            $queue = [System.Collections.Generic.Queue[int]]::new()
            $queue.Enqueue($idx)
            $visited[$idx] = $true
            $pixels = @()
            $sumX = 0

            while ($queue.Count -gt 0) {
                $cur = $queue.Dequeue()
                $cx = $cur % $w
                $cy = [int]($cur / $w)
                $pixels += $cur
                $sumX += $cx

                foreach ($d in $dirs) {
                    $nx = $cx + $d[0]
                    $ny = $cy + $d[1]
                    if ($nx -lt 0 -or $ny -lt 0 -or $nx -ge $w -or $ny -ge $h) { continue }
                    $nidx = $ny * $w + $nx
                    if ($visited[$nidx]) { continue }
                    if (-not (Test-SpritePixel $bmp.GetPixel($nx, $ny))) { continue }
                    $visited[$nidx] = $true
                    $queue.Enqueue($nidx)
                }
            }

            if ($pixels.Count -gt 0) {
                $components += [PSCustomObject]@{
                    Pixels = $pixels
                    Area   = $pixels.Count
                    MeanX  = $sumX / [double]$pixels.Count
                }
            }
        }
    }
    return $components
}

function Keep-PrimaryComponent([System.Drawing.Bitmap]$frame) {
    $components = Get-ConnectedComponents $frame
    if ($components.Count -le 1) { return $frame }

    $primary = $components | Sort-Object { $_.Area }, { $_.MeanX } -Descending | Select-Object -First 1
    $out = New-Object System.Drawing.Bitmap(
        $frame.Width, $frame.Height,
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
    )
    $g = [System.Drawing.Graphics]::FromImage($out)
    $g.Clear([System.Drawing.Color]::Transparent)
    $w = $frame.Width
    foreach ($idx in $primary.Pixels) {
        $x = $idx % $w
        $y = [int]($idx / $w)
        $out.SetPixel($x, $y, $frame.GetPixel($x, $y))
    }
    $g.Dispose()
    $frame.Dispose()
    return $out
}

function Save-CroppedFrame([System.Drawing.Bitmap]$src, [int]$x0, [int]$y0, [int]$w, [int]$h, [string]$path) {
    $bounds = Get-ContentBounds $src $x0 $y0 $w $h 8
    if ($null -eq $bounds) { return $false }
    $frame = New-Object System.Drawing.Bitmap $bounds.W, $bounds.H
    $g = [System.Drawing.Graphics]::FromImage($frame)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
    $dest = [System.Drawing.Rectangle]::new(0, 0, $bounds.W, $bounds.H)
    $srcRect = [System.Drawing.Rectangle]::new($bounds.X, $bounds.Y, $bounds.W, $bounds.H)
    $g.DrawImage($src, $dest, $srcRect, [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()

    $frame = Keep-PrimaryComponent $frame
    $trimmed = Get-ContentBounds $frame 0 0 $frame.Width $frame.Height 6
    if ($null -eq $trimmed) {
        $frame.Dispose()
        return $false
    }

    $final = New-Object System.Drawing.Bitmap $trimmed.W, $trimmed.H
    $g2 = [System.Drawing.Graphics]::FromImage($final)
    $g2.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $dest2 = [System.Drawing.Rectangle]::new(0, 0, $trimmed.W, $trimmed.H)
    $src2 = [System.Drawing.Rectangle]::new($trimmed.X, $trimmed.Y, $trimmed.W, $trimmed.H)
    $g2.DrawImage($frame, $dest2, $src2, [System.Drawing.GraphicsUnit]::Pixel)
    $g2.Dispose()
    $frame.Dispose()

    $final.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $final.Dispose()
    return $true
}

$srcPath = Join-Path $PSScriptRoot "..\src\assets\Raton\raton_spritesheet.png"
if (-not (Test-Path $srcPath)) {
    Write-Error "Missing spritesheet: $srcPath"
}

$base = Join-Path $PSScriptRoot "..\src\assets\Raton"
$anims = @(
    @{ folder = "Courir_animation";    prefix = "Courir"; frames = 6 },
    @{ folder = "Saut_animation";      prefix = "Saut";   frames = 5 },
    @{ folder = "accroupie_animation"; prefix = "accr";   frames = 4 }
)

$img = [System.Drawing.Bitmap]::FromFile((Resolve-Path $srcPath))
$rows = Get-RowBands $img
Write-Host "Detected $($rows.Count) sprite rows"

if ($rows.Count -lt 3) {
    Write-Error "Could not detect animation rows in spritesheet"
}

# Use first 3 content rows (run, jump, slide); ignore idle row if present
for ($r = 0; $r -lt 3; $r++) {
    $anim = $anims[$r]
    $row = $rows[$r]
    $destDir = Join-Path $base $anim.folder
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null

    $slices = Get-ColumnSlices $img $row.Y $row.H $anim.frames
    if ($slices.Count -ne $anim.frames) {
        Write-Warning "$($anim.folder): expected $($anim.frames) frames, got $($slices.Count) (check gap detection)"
    } else {
        Write-Host "$($anim.folder): $($slices.Count) frames via gap split"
    }

    for ($i = 0; $i -lt [Math]::Min($anim.frames, $slices.Count); $i++) {
        $slice = $slices[$i]
        $out = Join-Path $destDir ("{0}{1}.png" -f $anim.prefix, ($i + 1))
        $ok = Save-CroppedFrame $img $slice.X $row.Y $slice.W $row.H $out
        if (-not $ok) { Write-Warning "Empty frame: $out" }
    }
}

$img.Dispose()
Write-Host "Done. Tight-cropped frames written under $base"
