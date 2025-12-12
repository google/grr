import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {Browser} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';
import {CollectBrowserHistoryForm} from './collect_browser_history_form';
import {CollectBrowserHistoryFormHarness} from './testing/collect_browser_history_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(CollectBrowserHistoryForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectBrowserHistoryFormHarness,
  );
  return {fixture, harness};
}

describe('Collect Browser History Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectBrowserHistoryForm, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture} = await createComponent();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('calls onSubmit callback when submitting the form', async () => {
    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowName).toBe('CollectBrowserHistory');
        expect(flowArgs).toEqual({
          browsers: [
            Browser.CHROMIUM_BASED_BROWSERS,
            Browser.FIREFOX,
            Browser.INTERNET_EXPLORER,
            Browser.SAFARI,
          ],
        });
        onSubmitCalled = true;
      },
    );
    await (await harness.operaCheckbox()).uncheck();

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      collectChromiumBasedBrowsers: false,
      collectFirefox: true,
      collectInternetExplorer: true,
      collectOpera: false,
      collectSafari: false,
    });

    expect(flowArgs).toEqual({
      browsers: [Browser.FIREFOX, Browser.INTERNET_EXPLORER],
    });
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const formState = fixture.componentInstance.convertFlowArgsToFormState({
      browsers: [Browser.FIREFOX, Browser.INTERNET_EXPLORER],
    });

    expect(formState).toEqual({
      collectChromiumBasedBrowsers: false,
      collectFirefox: true,
      collectInternetExplorer: true,
      collectOpera: false,
      collectSafari: false,
    });
  });

  it('resets the flow args when passing flowArgs is called', async () => {
    const {harness} = await createComponent({
      browsers: [Browser.OPERA, Browser.SAFARI, Browser.FIREFOX],
    });
    expect(await (await harness.operaCheckbox()).isChecked()).toBeTrue();
    expect(await (await harness.safariCheckbox()).isChecked()).toBeTrue();
    expect(await (await harness.firefoxCheckbox()).isChecked()).toBeTrue();
    expect(
      await (await harness.chromiumBasedBrowsersCheckbox()).isChecked(),
    ).toBeFalse();
    expect(
      await (await harness.internetExplorerCheckbox()).isChecked(),
    ).toBeFalse();
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('initially shows all checkboxes checked', async () => {
    const {harness} = await createComponent();
    expect(
      await (await harness.chromiumBasedBrowsersCheckbox()).isChecked(),
    ).toBeTrue();
    expect(await (await harness.firefoxCheckbox()).isChecked()).toBeTrue();
    expect(
      await (await harness.internetExplorerCheckbox()).isChecked(),
    ).toBeTrue();
    expect(await (await harness.safariCheckbox()).isChecked()).toBeTrue();
    expect(await (await harness.operaCheckbox()).isChecked()).toBeTrue();
  });
});
