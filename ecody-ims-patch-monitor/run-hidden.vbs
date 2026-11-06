' eCoDY IMS - launch run.cmd with NO console window.
'
' Why this file exists:
'   The task runs under an Interactive logon, so cmd.exe shows a console
'   window. run.cmd sends everything to its log file, so that window sits
'   there completely blank for several minutes - it looks hung, and closing
'   it kills the run. wscript.exe itself draws no window, so launching
'   through here means no window appears at all.
'
' Run style 0 = hidden. True = wait for it to finish, so Task Scheduler
' keeps the task in Running state and still gets the real exit code
' (the watchdog and LastTaskResult depend on that).

Option Explicit

Dim sh, here, cmd, rc
Set sh = CreateObject("WScript.Shell")

here = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
cmd  = "cmd /c """ & here & "run.cmd"""

rc = sh.Run(cmd, 0, True)

WScript.Quit rc
