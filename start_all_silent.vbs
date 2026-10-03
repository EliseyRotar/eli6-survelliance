' eli6_silent_launcher.vbs
' Double-click this to start ELI6 surveillance without a console window
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\Users\eli6-admin\Documents\eli6-surveillance\start_all.bat" & chr(34), 0
Set WshShell = Nothing
