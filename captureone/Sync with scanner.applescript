-- Retrieve the current capture folder of the session opened in Capture One
tell application "Capture One 20"
	if (kind of current document) is not equal to session then
		display dialog "This script can only be used with sessions"
		return
	end if
	
	set capturesPath to (captures of current document)
end tell

display notification ("Starting synchronization to: " & (POSIX path of capturesPath))

do shell script "while true; do rsync -aP 'rsync://{{hostname}}/share' '" & (POSIX path of capturesPath) & "'; sleep 10; done"

display notification ("Finished synchronization")
