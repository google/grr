import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { ExpandableHash, HashTextAggregator } from './expandable_hash';
import { initTestEnvironment } from '@app/testing';

import { By } from '@angular/platform-browser';
import { Hash } from '@app/lib/api/api_interfaces';
import { DebugElement } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { ClipboardModule } from '@angular/cdk/clipboard';
import { MatIconModule } from '@angular/material/icon';

initTestEnvironment();

describe('ExpandableHash component', () => {
  let component: ExpandableHash;
  let fixture: ComponentFixture<ExpandableHash>;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      declarations: [ ExpandableHash ],
      imports: [
        ClipboardModule,
        MatMenuModule,
        MatButtonModule,
        MatIconModule,
      ],
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ExpandableHash);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  class ExpandableHashDOM {
    expandButton = this.root.query(By.css('.button-expand-expandable-hash-class'));
    expandButtonText = this.expandButton?.nativeElement.innerText;

    noHashesSpan = this.root.query(By.css('.no-hashes-expandable-hash-class'));
    noHashesSpanText = this.noHashesSpan?.nativeElement.innerText;

    constructor(readonly root: DebugElement) { }
  }

  function initComponentWithHashes(hashes: Hash): ExpandableHashDOM {
    component.hashes = hashes;
    fixture.detectChanges();
    return new ExpandableHashDOM(fixture.debugElement);
  }

  it('should only display an en dash (–) if no hashes are available', () => {
    const noHashes = { };
    const emDash = '–';

    const DOM = initComponentWithHashes(noHashes);

    expect(DOM.expandButton).toBeFalsy();

    expect(DOM.noHashesSpan).toBeTruthy();
    expect(DOM.noHashesSpanText).toBe(emDash);
  });

  it('should only display \"Copy value\" text if 1 hash is available', () => {
    const oneHash = {
      sha256: 'sha256',
    };

    initComponentWithHashes(oneHash);

    const DOM = initComponentWithHashes(oneHash);

    expect(DOM.noHashesSpan).toBeFalsy();

    expect(DOM.expandButton).toBeTruthy();
    expect(DOM.expandButtonText).toBe('Copy value');
  });
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
