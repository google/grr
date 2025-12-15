import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FileContent} from '../../../../../lib/models/vfs';
import {initTestEnvironment} from '../../../../../testing';
import {HexView} from './hex_view';
import {HexViewHarness} from './testing/hex_view_harness';

initTestEnvironment();

async function createComponent(blobContent: FileContent | undefined) {
  const fixture = TestBed.createComponent(HexView);
  fixture.componentRef.setInput('blobContent', blobContent);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    HexViewHarness,
  );

  return {fixture, harness};
}

describe('Hex View Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HexView, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent(undefined);

    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows complete hex and text content', async () => {
    const {harness} = await createComponent({
      totalLength: BigInt(100),
      blobContent: new Uint8Array([
        0x67, 0x6e, 0x6f, 0x6d, 0x65, 0x2d, 0x73, 0x63, 0x72, 0x65, 0x65, 0x6e,
        0x73, 0x68, 0x6f, 0x74, 0x50, 0x4e, 0x47,
      ]).buffer,
    });
    const hexTable = await harness.hexTable();
    const charsTable = await harness.charsTable();

    // Header offsets.
    expect(await hexTable.text()).toContain('0123456789ABCDEF');
    // Line offsets.
    expect(await hexTable.text()).toContain('000000');
    expect(await hexTable.text()).toContain('000010');
    // Hex content.
    expect(await hexTable.text()).toContain('676E6F6D652D73637265656E73686F74');
    expect(await hexTable.text()).toContain('504E47');
    // Text content
    expect(await charsTable.text()).toContain('gnome-screenshot');
    expect(await charsTable.text()).toContain('PNG');
  });
});
