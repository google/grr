import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {TimelineArgs} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {TimelineFormHarness} from './testing/timeline_form_harness';
import {TimelineForm} from './timeline_form';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(TimelineForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    TimelineFormHarness,
  );
  return {fixture, harness};
}

describe('Timeline Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [TimelineForm, NoopAnimationsModule],
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
        expect(flowName).toBe('TimelineFlow');
        expect(flowArgs).toEqual({
          root: btoa('/some/root/directory'),
        });
        onSubmitCalled = true;
      },
    );
    await harness.setRootDirectoryInput('/some/root/directory');

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      root: '/some/root/directory',
    });

    const expectedFlowArgs: TimelineArgs = {
      root: btoa('/some/root/directory'),
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: TimelineArgs = {
      root: btoa('/some/root/directory'),
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      root: '/some/root/directory',
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness} = await createComponent({
      root: btoa('/some/root/directory'),
    });

    expect(await harness.getRootDirectoryInput()).toBe('/some/root/directory');
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('displays warnings for knowledgebase expressions in root directory', async () => {
    const {harness} = await createComponent();

    await harness.setRootDirectoryInput(
      '%%some_kb_expression%%/and/some/**/glob_expressions/*',
    );
    const warnings = await harness.getRootDirectoryWarnings();
    // We show one hint with all warnings
    expect(warnings.length).toBe(1);
    expect(warnings[0]).toContain(
      'This path uses `%%` literally and will not evaluate any `%%knowledgebase_expressions%%`.',
    );
    expect(warnings[0]).toContain(
      'This path uses `*/**` literally and will not evaluate any paths with glob expressions.',
    );
  });
});
