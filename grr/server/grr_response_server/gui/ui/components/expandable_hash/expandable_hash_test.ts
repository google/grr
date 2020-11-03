import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpandableHash } from './expandable_hash';
import { initTestEnvironment } from '@app/testing';

import { OverlayModule } from '@angular/cdk/overlay';
import { By } from '@angular/platform-browser';
import { Hash } from '@app/lib/api/api_interfaces';

initTestEnvironment();

describe('ExpandableHash component', () => {
  let component: ExpandableHash;
  let fixture: ComponentFixture<ExpandableHash>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ExpandableHash ],
      imports: [ OverlayModule ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ExpandableHash);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  function getDisplayedHashText() {
    const hashDiv = fixture.debugElement.query(By.css('.truncated-hash'));
    return hashDiv.nativeElement.innerText;
  }

  function initComponentWithHashes(hashes: Hash) {
    component.hashes = hashes;
    fixture.detectChanges();
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
