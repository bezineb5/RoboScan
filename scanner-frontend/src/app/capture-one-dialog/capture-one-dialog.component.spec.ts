import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { CaptureOneDialogComponent } from './capture-one-dialog.component';

describe('CaptureOneDialogComponent', () => {
  let component: CaptureOneDialogComponent;
  let fixture: ComponentFixture<CaptureOneDialogComponent>;

  beforeEach(async(() => {
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
