import { Component, ViewChild } from '@angular/core';
import { FormGroup, FormControl } from '@angular/forms';
import { MatStepper } from '@angular/material/stepper';
import { MatDialog } from '@angular/material/dialog';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { Observable } from 'rxjs';
import { map, startWith } from 'rxjs/operators';

import { ScannerService, InlineObject4 } from '../lib/scanner';
import { BASE_PATH as ScannerApiUrl } from '../lib/scanner/variables';
import { environment } from 'src/environments/environment';
import { CameraStreamService, SessionEvent } from './camera-stream.service';
import { AlertDialogComponent } from './alert-dialog/alert-dialog.component';
import { DockerDialogComponent } from './docker-dialog/docker-dialog.component';
import { SambaDialogComponent } from './samba-dialog/samba-dialog.component';
import { RsyncDialogComponent } from './rsync-dialog/rsync-dialog.component';
import { CaptureOneDialogComponent } from './capture-one-dialog/capture-one-dialog.component';


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
  scannedPhotoCount: number = 0;
  // Show the "skip holes" feature?
  featureSkipHole: boolean = true;

  // Is a file move operation on-going? It will disable the start of a scan
  isMovingFiles: boolean = false;

  // Settings
  maxNumberOfFiles = "1";
  deletePhotoAfterDownload = false;

  // Autocompletes
  filmControl = new FormControl();
  filmMakersControl = new FormControl("");
  developProcessesControl = new FormControl();
  filteredFilms: Observable<FilmAutocomplete[]>;
  filteredFilmMakers: Observable<string[]>;
  filteredDevelopProcesses: Observable<string[]>;

  initialFrameCountControl = new FormControl("");
  lensSerialNumberControl = new FormControl("");
  rollIdControl = new FormControl("");
  filmAliasControl = new FormControl("");
  filmGrainControl = new FormControl(null);
  filmTypeControl = new FormControl("");
  developerControl = new FormControl("");
  developerMakerControl = new FormControl("");
  developerDilutionControl = new FormControl("");
  developTimeControl = new FormControl("");
  labControl = new FormControl("");
  labAddressControl = new FormControl("");
  filterControl = new FormControl("");

  filmTypes: string[];
  frameCounts: string[];
  films: FilmAutocomplete[];
  filmMakers: string[];

  // Camera settings
  cameraIsoControl = new FormControl("");
  cameraApertureControl = new FormControl("");
  cameraShutterSpeedControl = new FormControl("");
  cameraExposureCompensationControl = new FormControl("");

  isoChoices: string[];
  apertureChoices: string[];
  shutterSpeedChoices: string[];
  exposureCompensationChoices: string[];


  @ViewChild('scannerstepper')
  stepper: MatStepper;

  constructor(private scannerApi: ScannerService, private cameraStreamService: CameraStreamService, public dialog: MatDialog) { }

  ngOnInit() {
    this.initAutoComplete();
    this.getLastUsedSettings();

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
            this.scannedPhotoCount = 0;
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

  private initAutoComplete() {
    // Film types
    this.scannerApi.listFilmType().subscribe(data => {
      this.filmTypes = data.map((v, _i, _a) => v.type);
      if (this.filmTypeControl.value === "") {
        // This is a 35mm scanner
        this.filmTypeControl.setValue("135");
      }
    }, err => {
      console.log(err);
      this.filmTypes = ["135", "APS"];
      if (this.filmTypeControl.value === "") {
        this.filmTypeControl.setValue("135");
      }
      //this.openDialog("Error", err.error.message);
    });

    // Frame names
    this.scannerApi.listFrameCount().subscribe(data => {
      this.frameCounts = data.map((v, _i, _a) => v.frame);
    }, err => {
      console.log(err);
      this.frameCounts = ["00", "0", "1"];
      //this.openDialog("Error", err.error.message);
    });

    // Development processes
    this.scannerApi.listDevelopProcess().subscribe(data => {
      const developProcesses = data.map((v, _i, _a) => v.process);
      this.filteredDevelopProcesses = this.buildFilteredAutocomplete(this.developProcessesControl, developProcesses);
    }, err => {
      console.log(err);
      const developProcesses = ["BW", "C-41", "E-6"];
      this.filteredDevelopProcesses = this.buildFilteredAutocomplete(this.developProcessesControl, developProcesses);
      //this.openDialog("Error", err.error.message);
    });

    // Films
    this.scannerApi.listFilm().subscribe(data => {
      this.films = data.map((v, _i, _a) => { return { 'make': v.make, 'fullname': v.make + ' ' + v.name } });
      const extractFilmMakers = data.map((v, _i, _a) => v.make);
      this.filmMakers = Array.from(new Set(extractFilmMakers))
      this.filteredFilms = this.buildFilteredFilmAutocomplete(this.filmControl, this.films);
      this.filteredFilmMakers = this.buildFilteredAutocomplete(this.filmMakersControl, this.filmMakers);
    }, err => {
      console.log(err);
      const data = [{ "make": "KODAK", "name": "Gold 200" }, { "make": "FUJI", "name": "C200" }];
      this.films = data.map((v, _i, _a) => { return { 'make': v.make, 'fullname': v.make + ' ' + v.name } });
      this.filmMakers = data.map((v, _i, _a) => v.make);
      this.filteredFilms = this.buildFilteredFilmAutocomplete(this.filmControl, this.films);
      this.filteredFilmMakers = this.buildFilteredAutocomplete(this.filmMakersControl, this.filmMakers);
    });

    // Camera settings
    this.cameraExposureCompensationControl.valueChanges.subscribe(
      v => {
        this.scannerApi.setExposureCompensation({value: v}).subscribe(
          d => console.log(d),
          e => console.log(e)
        );
      }
    );
    this.cameraIsoControl.valueChanges.subscribe(
      v => {
        this.scannerApi.setIso({value: v}).subscribe(
          d => console.log(d),
          e => console.log(e)
        );
      }
    );
    this.cameraApertureControl.valueChanges.subscribe(
      v => {
        this.scannerApi.setAperture({value: v}).subscribe(
          d => console.log(d),
          e => console.log(e)
        );
      }
    );
    this.cameraShutterSpeedControl.valueChanges.subscribe(
      v => {
        this.scannerApi.setShutterSpeed({value: v}).subscribe(
          d => console.log(d),
          e => console.log(e)
        );
      }
    );
  }

  private getLastUsedSettings() {
    this.scannerApi.getLastUsedSettings().subscribe(
      data => {
        this.maxNumberOfFiles = data.max_number_of_files.toString();
        this.deletePhotoAfterDownload = data.delete_photo_after_download;

        this.initialFrameCountControl.setValue(data.initial_frame, {emitEvent: false});
        this.developProcessesControl.setValue(data.metadata_develop_process, {emitEvent: false});
        this.developTimeControl.setValue(data.metadata_develop_time, {emitEvent: false});
        this.developerControl.setValue(data.metadata_developer, {emitEvent: false});
        this.developerDilutionControl.setValue(data.metadata_developer_dilution, {emitEvent: false});
        this.developerMakerControl.setValue(data.metadata_developer_maker, {emitEvent: false});
        this.filmControl.setValue(data.metadata_film, {emitEvent: false});
        this.filmAliasControl.setValue(data.metadata_film_alias, {emitEvent: false});
        this.filmGrainControl.setValue(data.metadata_film_grain, {emitEvent: false});
        this.filmMakersControl.setValue(data.metadata_film_maker, {emitEvent: false});
        this.filmTypeControl.setValue(data.metadata_film_type, {emitEvent: false});
        this.filterControl.setValue(data.metadata_filter, {emitEvent: false});
        this.labControl.setValue(data.metadata_lab, {emitEvent: false});
        this.labAddressControl.setValue(data.metadata_lab_address, {emitEvent: false});
        this.lensSerialNumberControl.setValue(data.metadata_lens_serial_number, {emitEvent: false});
        this.rollIdControl.setValue(data.metadata_roll_id, {emitEvent: false});
      },
      e => console.log(e)
    );
  }

  private onSessionEvent(message: SessionEvent) {
    console.log("Websocket", message);

    switch (message.event) {
      case this.cameraStreamService.SessionStart:
        this.sessionId = message.id;
        this.scannedPhotoCount = 0;
        this.stepper.selectedIndex = this.StepCalibrate;
        break;
      case this.cameraStreamService.SessionStop:
        this.sessionId = undefined;
        this.scannedPhotoCount = 0;
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
    const metadata: InlineObject4 = {
      'max_number_of_files': parseInt(this.maxNumberOfFiles, 10),
      'delete_photo_after_download': this.deletePhotoAfterDownload,
      'initial_frame': this.initialFrameCountControl.value,
      'metadata_develop_process': this.developProcessesControl.value,
      'metadata_develop_time': this.developTimeControl.value,
      'metadata_developer': this.developerControl.value,
      'metadata_developer_dilution': this.developerDilutionControl.value,
      'metadata_developer_maker': this.developerMakerControl.value,
      'metadata_film': this.displayFilmName(this.filmControl.value),
      'metadata_film_alias': this.filmAliasControl.value,
      'metadata_film_grain': parseInt(this.filmGrainControl.value, 10),
      'metadata_film_maker': this.filmMakersControl.value,
      'metadata_film_type': this.filmTypeControl.value,
      'metadata_filter': this.filterControl.value,
      'metadata_lab': this.labControl.value,
      'metadata_lab_address': this.labAddressControl.value,
      'metadata_lens_serial_number': this.lensSerialNumberControl.value,
      'metadata_roll_id': this.rollIdControl.value,
    };

    if (environment.production) {
      this.scannerApi.initSession(metadata).subscribe(data => {
        console.log(data);

        this.featureSkipHole = data.feature_skip_hole;

        // Retrieve the camera settings
        this.getCameraSettingsChoices();

        // Move previous session to archive
        this.moveToArchive();
      }, err => {
        console.log(err);
        this.openDialog("Error", err.error.message);
      });
    } else {
      this.sessionId = 12345;
      this.stepper.next();
    }
  }

  getCameraSettingsChoices() {
    // ISO
    this.scannerApi.listIso().subscribe(data => {
      console.log(data);
      this.isoChoices = data.map((v, _i, _a) => v.value);
      
      let last_used_array = data.filter((v, _i, _a) => v.last_used == true);
      if (last_used_array.length > 0) {
        this.cameraIsoControl.setValue(last_used_array[0].value);
      }
    }, err => {
      console.log(err);
      this.openDialog("Error", err.error.message);
    });

    // Aperture
    this.scannerApi.listAperture().subscribe(data => {
      console.log(data);
      this.apertureChoices = data.map((v, _i, _a) => v.value);

      let last_used_array = data.filter((v, _i, _a) => v.last_used == true);
      if (last_used_array.length > 0) {
        this.cameraApertureControl.setValue(last_used_array[0].value);
      }
    }, err => {
      console.log(err);
      this.openDialog("Error", err.error.message);
    });

    // Shutter speed
    this.scannerApi.listShutterSpeed().subscribe(data => {
      console.log(data);
      this.shutterSpeedChoices = data.map((v, _i, _a) => v.value);

      let last_used_array = data.filter((v, _i, _a) => v.last_used == true);
      if (last_used_array.length > 0) {
        this.cameraShutterSpeedControl.setValue(last_used_array[0].value);
      }
    }, err => {
      console.log(err);
      this.openDialog("Error", err.error.message);
    });

    // Exposure compensation
    this.scannerApi.listExposureCompensation().subscribe(data => {
      console.log(data);
      this.exposureCompensationChoices = data.map((v, _i, _a) => v.value);

      let last_used_array = data.filter((v, _i, _a) => v.last_used == true);
      if (last_used_array.length > 0) {
        this.cameraExposureCompensationControl.setValue(last_used_array[0].value);
      }
    }, err => {
      console.log(err);
      this.openDialog("Error", err.error.message);
    });
  }

  moveToArchive() {
    this.isMovingFiles = true;

    this.scannerApi.moveToArchive().subscribe(data => {
      this.isMovingFiles = false;
      console.log(data);
    }, err => {
      this.isMovingFiles = false;
      console.log(err);
      this.openDialog("Error", err.error.message);
    });
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
    this.scannerApi.skipHoles(this.sessionId, { "number_of_holes": numberOfHoles }).subscribe(data => {
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
        this.stepper.reset();
      }, err => {
        console.log(err);
        // Refresh the page to reconnect with the active session, if any
        window.location.reload();
      });
    } else {
      this.sessionId = undefined;
      this.stepper.reset();
    }
  }

  onDeleteArchive() {
    this.isMovingFiles = true;

    this.scannerApi.deleteArchive().subscribe(data => {
      this.isMovingFiles = false;
      console.log(data);
    }, err => {
      this.isMovingFiles = false;
      console.log(err);
      this.openDialog("Error", err.error.message);
    });
  }

  openDialog(title: string, message: string) {
    this.dialog.open(AlertDialogComponent, {
      data: {
        title: title,
        message: message,
      }
    });
  }

  showDockerHelp() {
    this.dialog.open(DockerDialogComponent);
  }

  showSambaHelp() {
    this.dialog.open(SambaDialogComponent);
  }

  showRsyncHelp() {
    this.dialog.open(RsyncDialogComponent);
  }

  showCaptureOneHelp() {
    this.dialog.open(CaptureOneDialogComponent);
  }

  onFilmAutocompleteSelected(event: MatAutocompleteSelectedEvent) {
    console.log(this.filmMakersControl.value);
    if (typeof this.filmMakersControl.value !== 'string' || this.filmMakersControl.value === "") {
      const selectedFilm: FilmAutocomplete = event.option.value;
      this.filmMakersControl.setValue(selectedFilm.make);
    }
  }

  private _filter(optionsList: string[], value: string): string[] {
    const filterValue = value.toLowerCase();
    return optionsList.filter(option => option.toLowerCase().indexOf(filterValue) >= 0);
  }

  private buildFilteredAutocomplete(formControl: FormControl, optionsList: string[]): Observable<string[]> {
    return formControl.valueChanges.pipe(
      startWith(''),
      map(value => this._filter(optionsList, value))
    );
  };

  private _filterFilm(optionsList: FilmAutocomplete[], value: string | FilmAutocomplete): FilmAutocomplete[] {
    const filterValue = (<string>value).toLowerCase();

    return optionsList.filter(option => option.fullname.toLowerCase().indexOf(filterValue) >= 0);
  }

  private buildFilteredFilmAutocomplete(formControl: FormControl, optionsList: FilmAutocomplete[]): Observable<FilmAutocomplete[]> {
    return formControl.valueChanges.pipe(
      startWith(''),
      map(value => typeof value === 'string' ? value : value.fullname),
      map(value => this._filterFilm(optionsList, value))
    );
  };

  displayFilmName(film: FilmAutocomplete | string): string {
    if (typeof film == 'string') {
      return film;
    }

    return film && film.fullname ? film.fullname : '';
  }

}

export interface FilmAutocomplete {
  /**
   * Film brand name
   */
  make: string;
  /**
   * Film name (with the brand)
   */
  fullname: string;
}
