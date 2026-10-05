Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$proc = Start-Process pythonw -ArgumentList '"1.Python Code\Cloack_Overlay\Cloack_Overlay.pyw"' -PassThru
Start-Sleep -Seconds 3

$bounds = [System.Drawing.Rectangle]::FromLTRB(90, 90, 370, 500)
$bmp = New-Object System.Drawing.Bitmap ($bounds.Width, $bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bmp.Save('C:\Users\PythonX\.gemini\antigravity-ide\brain\dc3b2554-7403-4718-be5d-b5f2d78749b3\live_running_overlay.png')
$g.Dispose()
$bmp.Dispose()
Stop-Process -Id $proc.Id
Write-Host "Captured successfully!"
