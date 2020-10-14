import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { Hashes } from './hashes';

describe('Hashes', () => {
  let component: Hashes;
  let fixture: ComponentFixture<Hashes>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ Hashes ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(Hashes);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
