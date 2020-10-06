import { Component, OnInit, Inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-rsync-dialog',
  templateUrl: './rsync-dialog.component.html',
  styleUrls: ['./rsync-dialog.component.css']
})
export class RsyncDialogComponent implements OnInit {

  hostname = "<host>";
  scriptFile: SafeResourceUrl;

  private scriptTemplate = `set -euxo pipefail

if [ -n "$1" ]; then # First parameter = target destination
  DEST=$1
else
  DEST="."
fi

RSYNC_SRC="rsync://{{hostname}}/share"
SLEEP_TIME=10

echo "Synchronization started from $RSYNC_SRC to $DEST every \${SLEEP_TIME}s"

while [ : ]
do
    rsync -aP "$RSYNC_SRC" "$DEST"
    sleep $SLEEP_TIME
done
`;

  constructor(@Inject(DOCUMENT) private document: Document, private sanitizer: DomSanitizer) {}

  ngOnInit() {
    this.hostname = this.document.location.hostname;
    this.scriptFile = this.getScriptFile(this.hostname);
  }

  getScriptFile(hostname: string): SafeResourceUrl {
    const content = this.scriptTemplate.replace("{{hostname}}", hostname);
    const blob = new Blob([content], { type: 'application/x-sh' });
    return this.sanitizer.bypassSecurityTrustResourceUrl(window.URL.createObjectURL(blob));
  }
}
