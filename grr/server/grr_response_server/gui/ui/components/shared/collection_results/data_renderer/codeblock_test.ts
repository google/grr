import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../../testing';
import {Codeblock} from './codeblock';
import {CodeblockHarness} from './testing/codeblock_harness';

initTestEnvironment();

async function createComponent(code: readonly string[]) {
  const fixture = TestBed.createComponent(Codeblock);
  fixture.componentRef.setInput('code', code);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CodeblockHarness,
  );

  return {fixture, harness};
}

describe('Codeblock Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [Codeblock, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('renders code', async () => {
    const {harness} = await createComponent(['line1', 'line2']);

    const lines = await harness.linesText();
    expect(lines.length).toBe(2);
    expect(await lines[0]).toBe('line1');
    expect(await lines[1]).toBe('line2');
  });
});
