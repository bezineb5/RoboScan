import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { DockerDialogComponent } from './docker-dialog.component';

describe('DockerDialogComponent', () => {
  let component: DockerDialogComponent;
  let fixture: ComponentFixture<DockerDialogComponent>;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      declarations: [ DockerDialogComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(DockerDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
