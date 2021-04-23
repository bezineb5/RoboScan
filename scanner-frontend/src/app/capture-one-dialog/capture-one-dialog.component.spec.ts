import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { CaptureOneDialogComponent } from './capture-one-dialog.component';

describe('CaptureOneDialogComponent', () => {
  let component: CaptureOneDialogComponent;
  let fixture: ComponentFixture<CaptureOneDialogComponent>;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      declarations: [ CaptureOneDialogComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(CaptureOneDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
