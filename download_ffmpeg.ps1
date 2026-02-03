$ErrorActionPreference = "Stop"
$url = "https://github.com/GyanD/codexffmpeg/releases/download/7.0.2/ffmpeg-7.0.2-full_build.zip"
$zipPath = "ffmpeg_7.0.2.zip"
$extractPath = "ffmpeg_temp"
$destDir = "ffmpeg"

Write-Host "Downloading FFmpeg 7.0.2..."
Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host "Extracting..."
Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

Write-Host "Locating binary..."
$ffmpegParams = Get-ChildItem -Path $extractPath -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
if ($ffmpegParams) {
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir | Out-Null
    }
    
    $sourceBin = $ffmpegParams.DirectoryName
    Write-Host "Found binaries in $sourceBin"
    
    Copy-Item -Path "$sourceBin\ffmpeg.exe" -Destination $destDir -Force
    if (Test-Path "$sourceBin\ffprobe.exe") {
        Copy-Item -Path "$sourceBin\ffprobe.exe" -Destination $destDir -Force
    }
    
    Write-Host "FFmpeg installed to $destDir"
    
    # Cleanup
    Remove-Item -Path $zipPath -Force
    Remove-Item -Path $extractPath -Recurse -Force
    
    Write-Host "Done!"
} else {
    Write-Error "Could not find ffmpeg.exe in extraction"
}
