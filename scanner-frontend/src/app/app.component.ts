import { Component, ViewChild } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { MatStepper } from '@angular/material/stepper';
import { MatDialog } from '@angular/material/dialog';

import { ScannerService } from '../lib/scanner';
import { BASE_PATH as ScannerApiUrl } from '../lib/scanner/variables';
import { environment } from 'src/environments/environment';
import { CameraStreamService, SessionEvent } from './camera-stream.service';
import { AlertDialogComponent } from './alert-dialog/alert-dialog.component';


@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  providers: [{
    provide: ScannerApiUrl,
    useValue: "."
  }, ScannerService]
})
export class AppComponent {
  title = 'RoboScan';
  settingsGroup: FormGroup;

  private readonly StepPrepare = 0;
  private readonly StepCalibrate = 1;
  private readonly StepScanning = 2;
  private readonly StepFinished = 3;

  private sessionId: number = undefined;
  scannedPhotoCount: number = undefined;

  @ViewChild('scannerstepper')
  stepper: MatStepper;

  constructor(private scannerApi: ScannerService, private cameraStreamService: CameraStreamService, public dialog: MatDialog) { }

  ngOnInit() {
    // Init existing session
    this.scannerApi.listSessions().subscribe(s => {
      if (s && s.length > 0) {
        // The should be at most 1 session
        this.scannerApi.sessionDetails(s[0].id).subscribe(d => {
          this.sessionId = d.id;

          if (d.is_scanning) {
            // Session and scanning started
            this.stepper.selectedIndex = this.StepScanning;
          } else {
            // Session started, but no scanning
            this.scannedPhotoCount = undefined;
            this.stepper.selectedIndex = this.StepCalibrate;
          }
        });
      } else {
        // No session, start screen
        this.stepper.selectedIndex = this.StepPrepare;
      }
    });

    // Init websocket
    this.cameraStreamService.SessionEvents().subscribe(msg => this.onSessionEvent(msg));
  }

  private onSessionEvent(message: SessionEvent) {
    console.log("Websocket", message);
    
    switch (message.event) {
      case this.cameraStreamService.SessionStart:
        this.sessionId = message.id;
        this.scannedPhotoCount = undefined;
        this.stepper.selectedIndex = this.StepCalibrate;
        break;
      case this.cameraStreamService.SessionStop:
        this.sessionId = undefined;
        this.scannedPhotoCount = undefined;
        this.stepper.selectedIndex = this.StepFinished;
        break;
      case this.cameraStreamService.ScanStarted:
        this.stepper.selectedIndex = this.StepScanning;
        break;
      case this.cameraStreamService.ScannedPhoto:
        this.scannedPhotoCount = message.data + 1;
        break;
      case this.cameraStreamService.ScanFinished:
        this.scannedPhotoCount = message.data;
        break;
    }
  }

  onReadyToStart() {
    if (environment.production) {
      this.scannerApi.initSession().subscribe(data => {
        console.log(data);
      }, err => {
        console.log(err);
        this.openDialog("Error", err.error.message);
      });
    } else {
      this.sessionId = 12345;
      this.stepper.next();
    }
  }

  onStartScanning() {
    if (environment.production) {
      this.scannerApi.startScan(this.sessionId).subscribe(data => {
        console.log(data);
      });
    } else {
      this.stepper.next();
    }
  }

  onSkipHoles(numberOfHoles: number) {
    this.scannerApi.skipHoles({ "number_of_holes": numberOfHoles }, this.sessionId).subscribe(data => {
      console.log(data);
    });
  }

  onResetCamera() {
    this.scannerApi.resetCamera().subscribe(data => {
      console.log(data);
    }, err => {
      console.log(err);
      this.openDialog("Error", err.error.message);
    });
  }

  onCancel() {
    if (this.sessionId && environment.production) {
      this.scannerApi.stopSession(this.sessionId).subscribe(data => {
        console.log(data);
      }, err => {
        console.log(err);
        this.sessionId = undefined;
        this.stepper.reset();  
      });
    } else {
      this.sessionId = undefined;
      this.stepper.reset();
    }
  }

  openDialog(title: string, message: string) {
    this.dialog.open(AlertDialogComponent, {
      data: {
        title: title,
        message: message,
      }
    });
  }
}
