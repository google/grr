import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ExpandableHashModule} from '../../components/expandable_hash/module';
import {HexHash} from '../../lib/models/flow';
import {initTestEnvironment} from '../../testing';

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
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  class ExpandableHashDOM {
    harnessLoader = TestbedHarnessEnvironment.loader(this.rootFixture);

    expandButton = this.rootFixture.debugElement.query(
        By.css('.button-expand-expandable-hash-class'));
    expandButtonText = this.expandButton?.nativeElement.innerText;
    text = this.rootFixture.nativeElement.textContent;

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

  it('should be empty if no hashes are available', () => {
    const noHashes = {};

    const dom = initComponentWithHashes(noHashes);

    expect(dom.expandButton).toBeFalsy();
    expect(dom.text).toEqual('');
  });

  it('should show button with first hash name if a hash is available', () => {
    const oneHash = {
      sha256: 'testhash',
    };

    const dom = initComponentWithHashes(oneHash);

    expect(dom.expandButton).toBeTruthy();
    expect(dom.expandButtonText).toBe('SHA-256');
  });

  it('should display all hashes and copy-all item if all are available',
     async () => {
       const all3Hashes = {
         sha256: 'sha256value',
         sha1: 'sha1value',
         md5: 'md5value',
       };
       const dom = initComponentWithHashes(all3Hashes);

       expect(dom.expandButtonText).toBe('SHA-256 + 2');

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
