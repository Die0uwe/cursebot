' Start de bot onzichtbaar op de achtergrond (geen zwart venster)
Dim objShell, botPath
Set objShell = WScript.CreateObject("WScript.Shell")
botPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullPath)
objShell.Run "cmd /c """ & botPath & "\start_cursebot.bat""", 0, False
Set objShell = Nothing
