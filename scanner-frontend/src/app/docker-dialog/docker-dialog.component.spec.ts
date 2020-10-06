import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { DockerDialogComponent } from './docker-dialog.component';

describe('DockerDialogComponent', () => {
  let component: DockerDialogComponent;
  let fixture: ComponentFixture<DockerDialogComponent>;

  beforeEach(async(() => {
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
