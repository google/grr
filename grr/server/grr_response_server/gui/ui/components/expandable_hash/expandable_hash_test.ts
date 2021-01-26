import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ExpandableHashModule} from '@app/components/expandable_hash/module';

import {initTestEnvironment} from '@app/testing';
import {HexHash} from '../../lib/models/flow';
import {ExpandableHash} from './expandable_hash';


initTestEnvironment();

describe('ExpandableHash component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          declarations: [ExpandableHash],
          imports: [
            ExpandableHashModule,
            NoopAnimationsModule,
          ],

        })
        .compileComponents();
  }));

  class ExpandableHashDOM {
    harnessLoader = TestbedHarnessEnvironment.loader(this.rootFixture);

    expandButton = this.rootFixture.debugElement.query(
        By.css('.button-expand-expandable-hash-class'));
    expandButtonText = this.expandButton?.nativeElement.innerText;

    noHashesSpan = this.rootFixture.debugElement.query(
        By.css('.no-hashes-expandable-hash-class'));
    noHashesSpanText = this.noHashesSpan?.nativeElement.innerText;

    // Load harnesses lazily to prevent errors due to not-yet existing elements.
    get menuHarness() {
      return this.harnessLoader.getHarness(MatMenuHarness);
    }

    get expandButtonHarness() {
      return this.harnessLoader.getHarness<MatButtonHarness>(MatButtonHarness);
    }

    constructor(readonly rootFixture: ComponentFixture<ExpandableHash>) {}
  }

  function initComponentWithHashes(hashes: HexHash): ExpandableHashDOM {
    const fixture = TestBed.createComponent(ExpandableHash);
    fixture.componentInstance.hashes = hashes;
    fixture.detectChanges();

    return new ExpandableHashDOM(fixture);
  }

  it('should only display an en dash (–) if no hashes are available', () => {
    const noHashes = {};
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

  it('should display all hashes and copy-all item if all are available',
     async () => {
       const all3Hashes = {
         sha256: 'sha256value',
         sha1: 'sha1value',
         md5: 'md5value',
       };
       const dom = initComponentWithHashes(all3Hashes);

       const expandButton = await dom.expandButtonHarness;
       const expandedMenu = await dom.menuHarness;
       await expandButton.click();
       const menuItems = await expandedMenu.getItems();

       expect(menuItems.length).toBe(4);

       const textOfSha256 = await menuItems[0].getText();
       expect(textOfSha256).toContain('SHA-256');
       expect(textOfSha256).toContain('sha256value');

       const textOfSha1 = await menuItems[1].getText();
       expect(textOfSha1).toContain('SHA-1');
       expect(textOfSha1).toContain('sha1value');

       const textOfMd5 = await menuItems[2].getText();
       expect(textOfMd5).toContain('MD5');
       expect(textOfMd5).toContain('md5value');

       const textOfCopyAll = await menuItems[3].getText();
       expect(textOfCopyAll).toContain('All hash information');
     });
});
