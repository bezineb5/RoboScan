import { Component, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';

export interface AlertDialogData {
  title: string;
  message: string;
}

@Component({
  selector: 'app-alert-dialog',
  templateUrl: './alert-dialog.component.html',
})
export class AlertDialogComponent {

  message: string = ""
  closeButtonText = "Close"
  constructor(@Inject(MAT_DIALOG_DATA) public data: AlertDialogData) {}
}