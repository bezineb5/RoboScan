import { TestBed } from '@angular/core/testing';

import { CameraStreamService } from './camera-stream.service';

describe('CameraStreamService', () => {
  let service: CameraStreamService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(CameraStreamService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
