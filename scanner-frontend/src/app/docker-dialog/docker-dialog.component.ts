import { Component, OnInit, Inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';

@Component({
  selector: 'app-docker-dialog',
  templateUrl: './docker-dialog.component.html',
  styleUrls: ['./docker-dialog.component.css']
})
export class DockerDialogComponent implements OnInit {

  hostname = "<host>";

  constructor(@Inject(DOCUMENT) private document: Document) {}

  ngOnInit() {
    this.hostname = this.document.location.hostname;
  }
}
