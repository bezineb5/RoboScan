import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

// Angular Material
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatStepperModule } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDialogModule } from '@angular/material/dialog';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

// SocketIO
import { SocketIoModule, SocketIoConfig } from 'ngx-socket-io';

import { AppComponent } from './app.component';
import { AlertDialogComponent } from './alert-dialog/alert-dialog.component';
import { DockerDialogComponent } from './docker-dialog/docker-dialog.component';
import { SambaDialogComponent } from './samba-dialog/samba-dialog.component';
import { RsyncDialogComponent } from './rsync-dialog/rsync-dialog.component';
import { CaptureOneDialogComponent } from './capture-one-dialog/capture-one-dialog.component';

const config: SocketIoConfig = { url: '/scanner_events', options: {} };

@NgModule({
  declarations: [
    AppComponent,
    AlertDialogComponent,
    DockerDialogComponent,
    SambaDialogComponent,
    RsyncDialogComponent,
    CaptureOneDialogComponent
  ],
  imports: [
    HttpClientModule,
    BrowserModule,
    BrowserAnimationsModule,
    FormsModule,
    ReactiveFormsModule,
    MatToolbarModule,
    MatStepperModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatDialogModule,
    MatMenuModule,
    MatDividerModule,
    MatAutocompleteModule,
    MatInputModule,
    MatSelectModule,
    MatButtonToggleModule,
    MatExpansionModule,
    MatSlideToggleModule,
    SocketIoModule.forRoot(config),
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
