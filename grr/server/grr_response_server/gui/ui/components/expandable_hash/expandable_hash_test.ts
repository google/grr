import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpandableHash, truncateIfNeeded, MAX_CHARACTERS_IN_TRUNCATED_HASH} from './expandable_hash';
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

describe('truncateIfNeeded', () => {

  it('should truncate long text', () => {
    const textSize = MAX_CHARACTERS_IN_TRUNCATED_HASH + 100;

    const longText = 'a'.repeat(textSize);
    const truncated = truncateIfNeeded(longText);

    expect(truncated.length).toEqual(MAX_CHARACTERS_IN_TRUNCATED_HASH);
  })

  it('shouldn\'t truncate small text', () => {
    const textSize = MAX_CHARACTERS_IN_TRUNCATED_HASH;

    const shortText = 'a'.repeat(textSize);
    const truncated = truncateIfNeeded(shortText);

    expect(truncated.length).toEqual(textSize);
  })

  it('should put ellipsis to the truncated text', () => {
    const ellipsis = '...';

    const longText = 'thisisgoingtobeasha256hashprobably'.repeat(10);
    const expected = longText.slice(0, MAX_CHARACTERS_IN_TRUNCATED_HASH-ellipsis.length) + ellipsis;
    const truncated = truncateIfNeeded(longText);

    expect(truncated).toEqual(expected);
  })
})
