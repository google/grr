import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {OnlineNotificationArgs} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {OnlineNotificationForm} from './online_notification_form';
import {OnlineNotificationFormHarness} from './testing/online_notification_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(OnlineNotificationForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    OnlineNotificationFormHarness,
  );
  return {fixture, harness};
}

describe('Netstat Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [OnlineNotificationForm, NoopAnimationsModule],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture} = await createComponent();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('triggers onSubmit callback when submitting the form', async () => {
    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowName).toBe('OnlineNotification');
        expect(flowArgs).toEqual({
          email: 'test@example.com',
        });
        onSubmitCalled = true;
      },
    );

    await harness.setEmailInput('test@example.com');

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      email: 'test@example.com',
    });

    const expectedFlowArgs: OnlineNotificationArgs = {
      email: 'test@example.com',
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: OnlineNotificationArgs = {
      email: 'test@example.com',
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      email: 'test@example.com',
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness} = await createComponent({email: 'test@example.com'});

    expect(await harness.getEmailInput()).toBe('test@example.com');
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });
});
