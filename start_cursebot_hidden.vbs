' CurseBot - Slayer Alliance Edition
' Start de bot onzichtbaar op de achtergrond
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c """ & Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")) & "start_cursebot.bat""", 0, False
