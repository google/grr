import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpandableHash, truncateIfNeeded, TRUNCATED_HASH_CHAR_LIMIT, ELLIPSIS} from './expandable_hash';
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

  it('should truncate hash bigger than 7 symbols, keeping the first 6 and inserting an ellipsis', () => {
    const justSha256 = {sha256: '12345678'}
    initComponentWithHashes(justSha256);

    expect(getDisplayedHashText()).toEqual('123456' + ELLIPSIS);
  })

  it('should display \'SHA-256 n/a\' if no SHA-256', () => {
    const noSha256 = {
      md5: 'md5',
      sha1: 'sha1'
    };
    initComponentWithHashes(noSha256);

    expect(getDisplayedHashText()).toEqual('SHA-256 n/a');
  })
});

describe('truncateIfNeeded', () => {
  it('shouldn\'t modify small text', () => {
    const textSize = TRUNCATED_HASH_CHAR_LIMIT;

    const shortText = 'a'.repeat(textSize);
    const truncated = truncateIfNeeded(shortText);

    expect(truncated).toEqual(shortText);
  })

  it('should put ellipsis to the truncated text', () => {
    const longText = 'thisisgoingtobeasha256hashprobably'.repeat(10);
    const truncated = truncateIfNeeded(longText);

    const lastThreeSymbols = truncated.slice(-1);

    expect(lastThreeSymbols).toEqual(ELLIPSIS);
  })

  it('should truncate long text', () => {
    const textSize = TRUNCATED_HASH_CHAR_LIMIT + 100;

    const longText = 'a'.repeat(textSize);
    const truncated = truncateIfNeeded(longText);
    const withoutEllipsis = truncated.slice(0, -1);

    expect(truncated.length).toEqual(TRUNCATED_HASH_CHAR_LIMIT);
    expect(longText.startsWith(withoutEllipsis)).toBeTrue();
  })
})
