import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FileContent} from '../../../../../lib/models/vfs';
import {initTestEnvironment} from '../../../../../testing';
import {TextViewHarness} from './testing/text_view_harness';
import {TextView} from './text_view';

initTestEnvironment();

async function createComponent(textContent: FileContent | undefined) {
  const fixture = TestBed.createComponent(TextView);
  fixture.componentRef.setInput('textContent', textContent);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    TextViewHarness,
  );

  return {fixture, harness};
}

describe('Text View Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [TextView, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent(undefined);

    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows complete content', async () => {
    const {harness} = await createComponent({
      textContent: 'hello file content\nanother line',
      totalLength: BigInt(100),
    });

    const codeblock = await harness.codeblock();
    expect(await codeblock.linesText()).toEqual([
      'hello file content',
      'another line',
    ]);
  });
});
