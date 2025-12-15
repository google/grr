import {Clipboard} from '@angular/cdk/clipboard';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component, input, Type} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../testing';
import {CopyButton} from './copy_button';
import {CopyButtonHarness} from './testing/copy_button_harness';

initTestEnvironment();

@Component({
  template: `
      <copy-button [overrideCopyText]="overrideCopyText()">
        {{ content() }}
      </copy-button>`,
  imports: [CopyButton],
})
class TestTextButton {
  readonly overrideCopyText = input<string | undefined>(undefined);
  readonly content = input<string>('');
}

@Component({
  template: `
      <copy-button [overrideCopyText]="overrideCopyText()" >
        <div>{{ content() }}</div>
      </copy-button>`,
  imports: [CopyButton],
})
class TestComponentButton {
  readonly overrideCopyText = input<string | undefined>(undefined);
  readonly content = input<string>('');
}

async function createComponent<T extends TestTextButton | TestComponentButton>(
  testComponent: Type<T>,
) {
  const fixture = TestBed.createComponent(testComponent);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CopyButtonHarness,
  );
  return {fixture, harness};
}

describe('CopyButton component', () => {
  let clipboard: Partial<Clipboard>;

  beforeEach(() => {
    clipboard = {
      copy: jasmine.createSpy('copy').and.returnValue(true),
    };

    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, TestTextButton, TestComponentButton],
      providers: [
        {
          provide: Clipboard,
          useFactory: () => clipboard,
        },
      ],
    }).compileComponents();
  });

  it('renders text contents', async () => {
    const {fixture, harness} = await createComponent(TestTextButton);
    fixture.componentRef.setInput('content', 'test content');
    expect(await harness.getContentsText()).toEqual('test content');
  });

  it('renders component contents', async () => {
    const {fixture, harness} = await createComponent(TestComponentButton);
    fixture.componentRef.setInput('content', 'test content');
    expect(await harness.getContentsText()).toEqual('test content');
  });

  it('shows a copy confirmation when clicking on copy', async () => {
    const {fixture, harness} = await createComponent(TestTextButton);
    fixture.componentRef.setInput('content', 'test content');

    expect(await harness.isCheckIconVisible()).toBeFalse();
    expect(await harness.isCopyIconVisible()).toBeTrue();

    await harness.click();

    expect(await harness.isCheckIconVisible()).toBeTrue();
    expect(await harness.isCopyIconVisible()).toBeFalse();
  });

  it('copies the text content to the clipboard on click', async () => {
    const {fixture, harness} = await createComponent(TestTextButton);
    fixture.componentRef.setInput('content', 'test content');

    expect(clipboard.copy).not.toHaveBeenCalled();
    await harness.click();
    expect(clipboard.copy).toHaveBeenCalledOnceWith('test content');
  });

  it('copies the component content to the clipboard on click', async () => {
    const {fixture, harness} = await createComponent(TestComponentButton);
    fixture.componentRef.setInput('content', 'test content');

    expect(clipboard.copy).not.toHaveBeenCalled();
    await harness.click();
    expect(clipboard.copy).toHaveBeenCalledOnceWith('test content');
  });

  it('copies overrideCopyText if provided', async () => {
    const {fixture, harness} = await createComponent(TestTextButton);
    fixture.componentRef.setInput('content', 'test content');
    fixture.componentRef.setInput('overrideCopyText', 'overridden content');

    expect(await harness.getContentsText()).toEqual('test content');

    await harness.click();
    expect(clipboard.copy).toHaveBeenCalledOnceWith('overridden content');
  });
});
