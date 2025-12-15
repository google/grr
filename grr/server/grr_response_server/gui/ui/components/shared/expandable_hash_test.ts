import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HexHash} from '../../lib/models/flow';
import {initTestEnvironment} from '../../testing';
import {ExpandableHash} from './expandable_hash';
import {ExpandableHashHarness} from './testing/expandable_hash_harness';

initTestEnvironment();

async function createComponent(hashes: HexHash) {
  const fixture = TestBed.createComponent(ExpandableHash);
  // Set the default value here as the input is required.
  fixture.componentRef.setInput('hashes', hashes);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ExpandableHashHarness,
  );
  return {fixture, harness};
}

describe('Expandable Hash component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ExpandableHash, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('creates component', async () => {
    const {fixture} = await createComponent({});

    expect(fixture.componentInstance).toBeDefined();
  });

  it('should not show button if no hashes are available', async () => {
    const {harness} = await createComponent({});

    expect(await harness.hasButton()).toBeFalse();
    expect(await harness.hasMenu()).toBeFalse();
  });

  it('should show button with first hash name if a hash is available', async () => {
    const {harness} = await createComponent({sha256: 'testhash'});

    const button = await harness.getButton();

    expect(button).toBeDefined();
    expect(await button.getText()).toBe('SHA-256');
  });

  it('should show button with first hash name and +n if multiple hashes are available', async () => {
    const {harness} = await createComponent({
      sha256: 'testhash',
      sha1: 'testhash',
      md5: 'testhash',
    });

    const button = await harness.getButton();
    expect(await button.getText()).toBe('SHA-256 + 2');
  });

  it('should display all hashes in menu', async () => {
    const {harness} = await createComponent({
      sha256: 'sha256value',
      sha1: 'sha1value',
      md5: 'md5value',
    });
    const button = await harness.getButton();
    // expand menu
    await button.click();

    const menu = await harness.getMenu();
    const menuItems = await menu.getItems();

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
