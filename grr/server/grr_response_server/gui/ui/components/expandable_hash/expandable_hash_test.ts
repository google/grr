import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';

import {ExpandableHash} from './expandable_hash';
import {initTestEnvironment} from '@app/testing';

import {By} from '@angular/platform-browser';
import {Hash} from '@app/lib/api/api_interfaces';
import {DebugElement} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatMenuModule} from '@angular/material/menu';
import {ClipboardModule} from '@angular/cdk/clipboard';
import {MatIconModule} from '@angular/material/icon';

import {HarnessLoader} from '@angular/cdk/testing';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {MatButtonHarness} from '@angular/material/button/testing';

initTestEnvironment();

describe('ExpandableHash component', () => {
  let component: ExpandableHash;
  let fixture: ComponentFixture<ExpandableHash>;
  let harnessLoader: HarnessLoader;

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
    harnessLoader = TestbedHarnessEnvironment.loader(fixture);
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

    const dom = initComponentWithHashes(noHashes);

    expect(dom.expandButton).toBeFalsy();

    expect(dom.noHashesSpan).toBeTruthy();
    expect(dom.noHashesSpanText).toBe(emDash);
  });

  it('should only display \"Copy value\" text if 1 hash is available', () => {
    const oneHash = {
      sha256: 'sha256',
    };

    const dom = initComponentWithHashes(oneHash);

    expect(dom.noHashesSpan).toBeFalsy();

    expect(dom.expandButton).toBeTruthy();
    expect(dom.expandButtonText).toBe('Copy value');
  });

  fit('should display all three hashes and a copy button if all hashes are',
      async () => {
        const matButton  = await harnessLoader.getHarness<MatButtonHarness>(
            MatButtonHarness.with(),
        );
        await matButton.click();

        const expandedMenu = await harnessLoader.getHarness<MatMenuHarness>(
            MatMenuHarness.with({triggerText: 'Copy value'}));

        const menuItems = await expandedMenu.getItems();
        expect(menuItems.length).toBe(4);
      });
});
