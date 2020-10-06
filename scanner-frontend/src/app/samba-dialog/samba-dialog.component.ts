import { Component, OnInit, Inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';

@Component({
  selector: 'app-samba-dialog',
  templateUrl: './samba-dialog.component.html',
  styleUrls: ['./samba-dialog.component.css']
})
export class SambaDialogComponent implements OnInit {

  hostname = "<host>";

  constructor(@Inject(DOCUMENT) private document: Document) {}

  ngOnInit() {
    this.hostname = this.document.location.hostname;
  }
}
