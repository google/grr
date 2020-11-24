import { async, ComponentFixture, TestBed, tick, fakeAsync, waitForAsync } from '@angular/core/testing';

import { ExpandableHash, HashTextAggregator } from './expandable_hash';
import { initTestEnvironment } from '@app/testing';

import { By } from '@angular/platform-browser';
import { Hash } from '@app/lib/api/api_interfaces';
import { DebugElement } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { ClipboardModule } from '@angular/cdk/clipboard';

initTestEnvironment();

fdescribe('ExpandableHash component', () => {
  let component: ExpandableHash;
  let fixture: ComponentFixture<ExpandableHash>;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      declarations: [ ExpandableHash ],
      imports: [ ClipboardModule, MatMenuModule, MatButtonModule ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ExpandableHash);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  class ExpandableHashDOM {
    expandButton = this.root.query(By.css('.button-expand'));
    expandButtonText = this.expandButton?.nativeElement.innerText;

    noHashesSpan = this.root.query(By.css('.no-hashes'));
    noHashesSpanText = this.noHashesSpan?.nativeElement.innerText;

    copyMenu = this.root.query(By.css('mat-menu'));

    copyButtons = this.root.queryAll(By.css('button'));
    copyButtonsText = this.copyButtons.map(button => button.nativeElement.innerText);

    constructor(readonly root: DebugElement) { }
  }

  function initComponentWithHashes(hashes: Hash): ExpandableHashDOM {
    component.hashes = hashes;
    fixture.detectChanges();
    return new ExpandableHashDOM(fixture.debugElement);
  }

  function expandMenu(oldDOM: ExpandableHashDOM): ExpandableHashDOM {
    oldDOM.expandButton.triggerEventHandler('click', null);
    oldDOM.expandButton.nativeElement.click();
    tick();
    fixture.detectChanges();
    return new ExpandableHashDOM(fixture.debugElement);
  }

  it('should display en dash (–) if no hashes are available', () => {
    const noHashes = { };
    const emDash = '–';

    const DOM = initComponentWithHashes(noHashes);

    expect(DOM.noHashesSpan).toBeTruthy();
    expect(DOM.noHashesSpanText).toBe(emDash);
  });

  it('should display \"Copy value\" text if 1 hash is available', () => {
    const oneHash = {
      sha256: 'sha256',
    };

    initComponentWithHashes(oneHash);

    const DOM = initComponentWithHashes(oneHash);

    expect(DOM.expandButton).toBeTruthy();
    expect(DOM.expandButtonText).toBe('Copy value');
  });

  it('should\'t display menu button "Copy all" if just 1 hash is present', fakeAsync(() => {
    const oneHash = {
      sha256: 'sha256',
    };
    const initialDOM = initComponentWithHashes(oneHash);
    const DOM = expandMenu(initialDOM);

    expect(DOM.copyMenu).toBeTruthy();
    expect(DOM.copyButtons.length).toBe(1);
    expect(DOM.copyButtonsText[0]).not.toBe('Copy all');
  }));

  // it('should display copy all with text if 2 hashes are present', () => {
  //   const twoHashes = {
  //     sha256: 'sha256',
  //     md5: 'md5',
  //   };
  //   const fixture = createComponentFixtureWith(twoHashes);

  //   const copyAllDiv = fixture.debugElement.query(By.css('.copy-all-section'));
  //   const copyAllText = copyAllDiv.query(By.css('.copy-all-text')).nativeElement.innerText;

  //   expect(copyAllDiv).toBeTruthy();
  //   expect(copyAllText).toBe('All hash information');
  // });

  // it('should display SHA-256 hash', () => {
  //   const sha256Only = {
  //     sha256: 'sha256-0123456789abcdef'
  //   };

  //   const expectedHashName = 'SHA-256'
  //   const expectedHashValue = sha256Only.sha256;

  //   const fixture = createComponentFixtureWith(sha256Only);
  //   const displayedHashes = getDisplayedHashes(fixture);

  //   expect(displayedHashes.length).toEqual(1);
  //   expect(displayedHashes[0].hashType).toEqual(expectedHashName);
  //   expect(displayedHashes[0].value).toEqual(expectedHashValue);
  // });

  // it('should display SHA-1 hash', () => {
  //   const sha1Only = {
  //     sha1: 'sha1-0123456789abcdef'
  //   };

  //   const expectedHashName = 'SHA-1'
  //   const expectedHashValue = sha1Only.sha1;

  //   const fixture = createComponentFixtureWith(sha1Only);
  //   const displayedHashes = getDisplayedHashes(fixture);

  //   expect(displayedHashes.length).toEqual(1);
  //   expect(displayedHashes[0].hashType).toEqual(expectedHashName);
  //   expect(displayedHashes[0].value).toEqual(expectedHashValue);
  // });

  // it('should display MD5 hash', () => {
  //   const md5Only = {
  //     md5: 'md5-0123456789abcdef'
  //   };

  //   const expectedHashName = 'MD5'
  //   const expectedHashValue = md5Only.md5;

  //   const fixture = createComponentFixtureWith(md5Only);
  //   const displayedHashes = getDisplayedHashes(fixture);

  //   expect(displayedHashes.length).toEqual(1);
  //   expect(displayedHashes[0].hashType).toEqual(expectedHashName);
  //   expect(displayedHashes[0].value).toEqual(expectedHashValue);
  // });

  // it('should display all SHA-256, SHA-1 and MD5', () => {
  //   const allHashes = {
  //     sha256: 'sha256-0123456789abcdef',
  //     sha1: 'sha1-0123456789abcdef',
  //     md5: 'md5-0123456789abcdef',
  //   };

  //   const fixture = createComponentFixtureWith(allHashes);
  //   const displayedHashes = getDisplayedHashes(fixture);

  //   expect(displayedHashes.length).toEqual(3);
  //   expect(displayedHashes[0].hashType).toEqual('SHA-256');
  //   expect(displayedHashes[0].value).toEqual(allHashes.sha256);

  //   expect(displayedHashes[1].hashType).toEqual('SHA-1');
  //   expect(displayedHashes[1].value).toEqual(allHashes.sha1);

  //   expect(displayedHashes[2].hashType).toEqual('MD5');
  //   expect(displayedHashes[2].value).toEqual(allHashes.md5);
  // });
});

describe('HashTextAggregator', () => {
  it('should produce an empty string when no hashes are added', () => {
    const hashText = new HashTextAggregator();

    expect(hashText.toString()).toEqual('');
  });

  it('should include the type of the hash', () => {
    const hashText = new HashTextAggregator();
    const hashType = 'MD5';
    const expectedBeginning = `${hashType}:`;

    hashText.appendHashTypeAndValue(hashType, 'random');

    expect(hashText.toString().startsWith(expectedBeginning)).toBeTrue();
  });

  it('should add a newline before subsequent hashes', () => {
    const hashText = new HashTextAggregator();
    const expectedString = 'type1: hash1\ntype2: hash2\ntype3: hash3';

    hashText.appendHashTypeAndValue('type1', 'hash1');
    hashText.appendHashTypeAndValue('type2', 'hash2');
    hashText.appendHashTypeAndValue('type3', 'hash3');

    expect(hashText.toString()).toEqual(expectedString);
  });
});
