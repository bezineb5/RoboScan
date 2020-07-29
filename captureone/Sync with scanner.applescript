-- Retrieve the current capture folder of the session opened in Capture One
tell application "Capture One 20"
	if (kind of current document) is not equal to session then
		display dialog "This script can only be used with sessions"
		return
	end if
	
	set capturesPath to (captures of current document)
end tell

set the clipboard to (POSIX path of capturesPath)
display notification ("Copied: " & (POSIX path of capturesPath))
