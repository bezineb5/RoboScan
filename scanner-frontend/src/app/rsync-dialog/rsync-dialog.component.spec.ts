import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { RsyncDialogComponent } from './rsync-dialog.component';

describe('RsyncDialogComponent', () => {
  let component: RsyncDialogComponent;
  let fixture: ComponentFixture<RsyncDialogComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ RsyncDialogComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(RsyncDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
