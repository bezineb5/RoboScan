import { Component, OnInit, Inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-capture-one-dialog',
  templateUrl: './capture-one-dialog.component.html',
  styleUrls: ['./capture-one-dialog.component.css']
})
export class CaptureOneDialogComponent implements OnInit {

  hostname = "<host>";
  scriptFile: SafeResourceUrl;

  private scriptTemplate = `-- Retrieve the current capture folder of the session opened in Capture One
tell application "Capture One 20"
  if (kind of current document) is not equal to session then
    display dialog "This script can only be used with sessions"
    return
  end if
  
  set capturesPath to (captures of current document)
end tell

display notification ("Starting synchronization to: " & (POSIX path of capturesPath))

repeat
	do shell script "rsync -aP 'rsync://{{hostname}}/share' '" & (POSIX path of capturesPath) & "'"
	delay 10
end repeat

display notification ("Finished synchronization")
`;

  constructor(@Inject(DOCUMENT) private document: Document, private sanitizer: DomSanitizer) { }

  ngOnInit() {
    this.hostname = this.document.location.hostname;
    this.scriptFile = this.getScriptFile(this.hostname);
  }

  getScriptFile(hostname: string): SafeResourceUrl {
    const content = this.scriptTemplate.replace("{{hostname}}", hostname);
    const blob = new Blob([content], { type: 'application/x-applescript' });
    return this.sanitizer.bypassSecurityTrustResourceUrl(window.URL.createObjectURL(blob));
  }
}
