import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpandableHash } from './expandable_hash';
import { initTestEnvironment } from '@app/testing';

initTestEnvironment();

fdescribe('HashComponent', () => { // TODO: Remove f
  let component: ExpandableHash;
  let fixture: ComponentFixture<ExpandableHash>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ExpandableHash ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ExpandableHash);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

fdescribe('truncateIfNeeded', () => { // TODO: Remove f
  it('should truncate text bigger than the specified', () => {
    const maxSize = 10;
    const textSize = 20;

    const longText = 'a'.repeat(textSize);
    const truncated = ExpandableHash.truncateIfNeeded(longText, maxSize);

    expect(truncated.length).toEqual(maxSize);
  })

  it('shouldn\'t truncate text smaller or equal to the specified', () => {
    const maxSize = 10;
    const textSize = 5;

    const shortText = 'a'.repeat(textSize);
    const truncated = ExpandableHash.truncateIfNeeded(shortText, maxSize);

    expect(truncated.length).toEqual(textSize);
  })

  it('should put ellipsis to the truncated text', () => {
    const maxSize = 10;

    const longText = 'thisisgoingtobeasha256hashprobably';
    const expected = longText.slice(0, maxSize-3) + '...';
    const truncated = ExpandableHash.truncateIfNeeded(longText, maxSize);

    expect(truncated).toEqual(expected);
  })
})
