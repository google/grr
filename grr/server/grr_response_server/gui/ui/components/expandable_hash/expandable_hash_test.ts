import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ExpandableHash, truncateIfNeeded, MAX_CHARACTERS_IN_TRUNCATED_HASH} from './expandable_hash';
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
    const hashDiv = fixture.debugElement.query(By.css('.truncatedHash'));
    return hashDiv.nativeElement.innerText;
  }

  function initComponentWithHashes(hashes: Hash) {
    component.hashes = hashes;
    fixture.detectChanges();
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should truncate hash bigger than 9 symbols, keeping the first 6 and inserting an ellipsis', () => {
    const justSha256 = {sha256: '1234567890'}
    initComponentWithHashes(justSha256);

    expect(getDisplayedHashText()).toEqual('123456...');
  })

  it('should display \'sha 256 n/a\' if no sha256', () => {
    const noSha256 = {
      md5: 'md5',
      sha1: 'sha1'
    };
    initComponentWithHashes(noSha256);

    expect(getDisplayedHashText()).toEqual('sha256 n/a');
  })
});

describe('truncateIfNeeded', () => {
  it('shouldn\'t modify small text', () => {
    const textSize = MAX_CHARACTERS_IN_TRUNCATED_HASH;

    const shortText = 'a'.repeat(textSize);
    const truncated = truncateIfNeeded(shortText);

    expect(truncated).toEqual(shortText);
  })

  it('should put ellipsis to the truncated text', () => {
    const ellipsis = '...';

    const longText = 'thisisgoingtobeasha256hashprobably'.repeat(10);
    const truncated = truncateIfNeeded(longText);

    const lastThreeSymbols = truncated.slice(-3);

    expect(lastThreeSymbols).toEqual(ellipsis);
  })

  it('should truncate long text', () => {
    const textSize = MAX_CHARACTERS_IN_TRUNCATED_HASH + 100;

    const longText = 'a'.repeat(textSize);
    const truncated = truncateIfNeeded(longText);
    const withoutEllipsis = truncated.slice(0, -3);

    expect(truncated.length).toEqual(MAX_CHARACTERS_IN_TRUNCATED_HASH);
    expect(longText.startsWith(withoutEllipsis)).toBeTrue();
  })
})
