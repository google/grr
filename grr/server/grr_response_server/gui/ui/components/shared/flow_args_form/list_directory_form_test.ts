import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ListDirectoryArgs} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {PathSpecPathType} from '../../../lib/models/vfs';
import {GlobalStore} from '../../../store/global_store';
import {newGlobalStoreMock} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ListDirectoryForm} from './list_directory_form';
import {ListDirectoryFormHarness} from './testing/list_directory_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(ListDirectoryForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ListDirectoryFormHarness,
  );
  return {fixture, harness};
}

describe('List Directory Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ListDirectoryForm, NoopAnimationsModule],
      providers: [
        {provide: GlobalStore, useValue: newGlobalStoreMock()},
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
        expect(flowName).toBe('ListDirectory');
        expect(flowArgs).toEqual({
          pathspec: {
            pathtype: PathSpecPathType.OS,
            path: '/some/path',
          },
        });
        onSubmitCalled = true;
      },
    );
    await harness.selectCollectionMethod('OS');
    await harness.setPathInput('/some/path');

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      collectionMethod: PathSpecPathType.TSK,
      path: '/some/path',
    });

    const expectedFlowArgs: ListDirectoryArgs = {
      pathspec: {
        pathtype: PathSpecPathType.TSK,
        path: '/some/path',
      },
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: ListDirectoryArgs = {
      pathspec: {
        pathtype: PathSpecPathType.TSK,
        path: '/some/path',
      },
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      collectionMethod: PathSpecPathType.TSK,
      path: '/some/path',
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness, fixture} = await createComponent();
    fixture.componentInstance.resetFlowArgs({
      pathspec: {
        pathtype: PathSpecPathType.TSK,
        path: '/some/path',
      },
    });
    expect(await harness.getCollectionMethod()).toBe(PathSpecPathType.TSK);
    expect(await harness.getPathInput()).toBe('/some/path');
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });
});
