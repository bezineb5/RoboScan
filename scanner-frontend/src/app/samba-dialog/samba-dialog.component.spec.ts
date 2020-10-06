import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { SambaDialogComponent } from './samba-dialog.component';

describe('SambaDialogComponent', () => {
  let component: SambaDialogComponent;
  let fixture: ComponentFixture<SambaDialogComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ SambaDialogComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SambaDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
