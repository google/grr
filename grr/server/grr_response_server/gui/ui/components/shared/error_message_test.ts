import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../testing';
import {ErrorMessage} from './error_message';
import {ErrorMessageHarness} from './testing/error_message_harness';

initTestEnvironment();

async function createComponent(message: string) {
  const fixture = TestBed.createComponent(ErrorMessage);
  fixture.componentRef.setInput('message', message);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ErrorMessageHarness,
  );
  return {fixture, harness};
}

describe('Error Message Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ErrorMessage, NoopAnimationsModule],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent('');

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows the correct message', async () => {
    const {harness} = await createComponent('test message');

    expect(await harness.getMessage()).toBe('test message');
  });

  it('shows \\n as new lines', async () => {
    const {harness} = await createComponent('test message\nsecond line');

    expect(await harness.getMessage()).toBe('test message\nsecond line');
  });

  it('keeps \\\\n as is', async () => {
    const {harness} = await createComponent('test message\\nsame line');

    expect(await harness.getMessage()).toBe('test message\\nsame line');
  });
});
