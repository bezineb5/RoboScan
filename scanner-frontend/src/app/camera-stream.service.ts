import { Injectable } from '@angular/core';
import { Socket } from 'ngx-socket-io';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class CameraStreamService {
  public readonly SessionStart = "start";
  public readonly SessionStop = "stop";
  public readonly ScanStarted = "scan_started";
  public readonly ScannedPhoto = "scanned_photo";
  public readonly ScanFinished = "scan_finished";

  constructor(private socket: Socket) { 
    this.socket.on('connect', () => {
      console.log("Connected");
    });
  }

  private onSessionEvent(message) {
    if (message && "event" in message) {
      const event: string = message['event'];
      const data: string = "data" in message ? message["data"] : undefined;
      console.log(event, data);
    } else {
      console.log("Wrong message received: ", message)
    }
  }

  public SessionEvents(): Observable<SessionEvent> {
    this.socket.on('session', (msg) => this.onSessionEvent(msg));
    return this.socket.fromEvent<SessionEvent>('session')
  }
}

export interface SessionEvent {
  event: string,
  id: number,
  data?: number,
}