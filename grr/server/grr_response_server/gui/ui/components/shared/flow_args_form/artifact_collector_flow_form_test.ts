import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {
  ArtifactDescriptor,
  OperatingSystem,
  SourceType,
} from '../../../lib/models/flow';
import {
  newArtifactDescriptor,
  newArtifactSourceDescription,
} from '../../../lib/models/model_test_util';
import {GlobalStore} from '../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ArtifactCollectorFlowForm} from './artifact_collector_flow_form';
import {ArtifactCollectorFlowFormHarness} from './testing/artifact_collector_flow_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(ArtifactCollectorFlowForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ArtifactCollectorFlowFormHarness,
  );
  return {fixture, harness};
}

describe('Artifact Collector Flow Form Component', () => {
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [ArtifactCollectorFlowForm, NoopAnimationsModule],
      providers: [
        {provide: GlobalStore, useValue: globalStoreMock},
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
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('triggers onSubmit callback when submitting the form', fakeAsync(async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'AmazingArtifact',
      newArtifactDescriptor({name: 'AmazingArtifact'}),
    );
    globalStoreMock.artifactDescriptorMap = signal(artifactDescriptorMap);
    tick();

    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowName).toBe('ArtifactCollectorFlow');
        expect(flowArgs).toEqual({artifactList: ['AmazingArtifact']});
        onSubmitCalled = true;
      },
    );
    const submitButton = await harness.getSubmitButton();
    const autocompleteHarness = await harness.autocompleteHarness();
    await autocompleteHarness.enterText('AmazingArtifact');
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  }));

  it('disables submit button when form is invalid', fakeAsync(async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'AmazingArtifact',
      newArtifactDescriptor({name: 'AmazingArtifact'}),
    );
    globalStoreMock.artifactDescriptorMap = signal(artifactDescriptorMap);
    tick();

    const {harness} = await createComponent();
    const submitButton = await harness.getSubmitButton();
    expect(await submitButton.isDisabled()).toBeTrue();
    const autocompleteHarness = await harness.autocompleteHarness();
    await autocompleteHarness.enterText('AmazingArtifact');
    expect(await submitButton.isEnabled()).toBeTrue();
    await autocompleteHarness.enterText('not matching flow name');
    expect(await submitButton.isDisabled()).toBeTrue();
  }));

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      artifactName: 'AmazingArtifact',
    });
    expect(flowArgs).toEqual({artifactList: ['AmazingArtifact']});
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const formState = fixture.componentInstance.convertFlowArgsToFormState({
      artifactList: ['AmazingArtifact'],
    });
    expect(formState).toEqual({artifactName: 'AmazingArtifact'});
  });

  it('can get control of form-field', async () => {
    const {harness} = await createComponent();
    const formField = await harness.form();
    expect((await formField.getControl()) instanceof MatInputHarness).toBe(
      true,
    );
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact1',
      newArtifactDescriptor({name: 'artifact1'}),
    );
    artifactDescriptorMap.set(
      'artifact2',
      newArtifactDescriptor({name: 'artifact2'}),
    );
    globalStoreMock.artifactDescriptorMap = signal(artifactDescriptorMap);

    const {fixture, harness} = await createComponent();
    fixture.componentInstance.resetFlowArgs({
      artifactList: ['artifact2'],
    });
    const autocompleteHarness = await harness.autocompleteHarness();
    expect(await autocompleteHarness.getValue()).toContain('artifact2');
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('displays the options based on the artifacts', fakeAsync(async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact1',
      newArtifactDescriptor({
        name: 'artifact1',
        doc: 'artifact1 doc',
        supportedOs: new Set([OperatingSystem.LINUX]),
        sourceDescriptions: [
          newArtifactSourceDescription({
            collections: ['source1', 'source2'],
          }),
        ],
      }),
    );
    artifactDescriptorMap.set(
      'artifact2',
      newArtifactDescriptor({
        name: 'artifact2',
        supportedOs: new Set([OperatingSystem.WINDOWS, OperatingSystem.DARWIN]),
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(
      new Map<string, ArtifactDescriptor>(artifactDescriptorMap),
    );
    tick();

    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('clientOs', 'Linux');

    const autocompleteHarness = await harness.autocompleteHarness();
    await autocompleteHarness.enterText('artifact');
    tick();
    const artifactOptions = await autocompleteHarness.getOptions();
    expect(artifactOptions.length).toBe(2);
    const firstArtifactOption = await artifactOptions[0];
    expect(await firstArtifactOption.isDisabled()).toBeFalse();
    expect(await firstArtifactOption.getText()).toContain('artifact1');
    expect(await firstArtifactOption.getText()).toContain('artifact1 doc');
    expect(await firstArtifactOption.getText()).toContain('source1');

    const secondArtifactOption = await artifactOptions[1];
    expect(await secondArtifactOption.isDisabled()).toBeTrue();
    expect(await secondArtifactOption.getText()).toContain('artifact2');
    expect(await secondArtifactOption.getText()).toContain(
      'Only available on Windows, Darwin',
    );
  }));

  it('emits a valid form validation when selecting an artifact', fakeAsync(async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'a very specific artifact',
      newArtifactDescriptor({
        name: 'a very specific artifact',
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(artifactDescriptorMap);
    tick();

    const {harness} = await createComponent();
    const form = await harness.form();
    expect(await form.isControlValid()).toBeFalse();

    const autocompleteHarness = await harness.autocompleteHarness();
    await autocompleteHarness.enterText('artifact');
    expect(await form.isControlValid()).toBeFalse();

    await autocompleteHarness.selectOption({text: 'a very specific artifact'});
    expect(await form.isControlValid()).toBeTrue();
  }));

  it('filters options based on input', fakeAsync(async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'artifact1',
      newArtifactDescriptor({
        name: 'artifact1',
      }),
    );
    artifactDescriptorMap.set(
      'artifact2',
      newArtifactDescriptor({
        name: 'artifact2',
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(
      new Map<string, ArtifactDescriptor>(artifactDescriptorMap),
    );
    tick();

    const {harness} = await createComponent();

    const autocompleteHarness = await harness.autocompleteHarness();
    await autocompleteHarness.enterText('artifact');
    tick();
    const artifactOptions = await autocompleteHarness.getOptions();
    expect(artifactOptions.length).toBe(2);
    expect(await artifactOptions[0].getText()).toContain('artifact1');
    expect(await artifactOptions[1].getText()).toContain('artifact2');

    await autocompleteHarness.clear();
    await autocompleteHarness.enterText('artifact1');
    tick();
    const filteredArtifactOptions = await autocompleteHarness.getOptions();
    expect(filteredArtifactOptions.length).toBe(1);
    expect(await filteredArtifactOptions[0].getText()).toContain('artifact1');
  }));

  it('displays the artifact details when selected', fakeAsync(async () => {
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>();
    artifactDescriptorMap.set(
      'Shopping List',
      newArtifactDescriptor({
        name: 'Shopping List',
        doc: 'artifact1 doc',
        supportedOs: new Set([OperatingSystem.LINUX]),
        artifacts: [
          newArtifactDescriptor({
            name: 'Veggies',
            supportedOs: new Set([OperatingSystem.LINUX]),

            sourceDescriptions: [
              newArtifactSourceDescription({
                type: SourceType.FILE,
                supportedOs: new Set([OperatingSystem.LINUX]),
                collections: ['Cucumber'],
              }),
            ],
          }),
          newArtifactDescriptor({
            name: 'Fruits',
            supportedOs: new Set([OperatingSystem.LINUX]),
            sourceDescriptions: [
              newArtifactSourceDescription({
                type: SourceType.REGISTRY_KEY,
                supportedOs: new Set([OperatingSystem.LINUX]),
                collections: ['Apple', 'Banana'],
              }),
            ],
            artifacts: [
              newArtifactDescriptor({
                name: 'Exotic Fruits',
                supportedOs: new Set([OperatingSystem.LINUX]),
                sourceDescriptions: [
                  newArtifactSourceDescription({
                    type: SourceType.FILE,
                    supportedOs: new Set([OperatingSystem.LINUX]),
                    collections: ['Mango'],
                  }),
                ],
              }),
            ],
          }),
        ],
      }),
    );
    globalStoreMock.artifactDescriptorMap = signal(
      new Map<string, ArtifactDescriptor>(artifactDescriptorMap),
    );
    tick();

    const {harness} = await createComponent();
    const autocompleteHarness = await harness.autocompleteHarness();
    await autocompleteHarness.enterText('artifact');
    tick();
    const artifactOptions = await autocompleteHarness.getOptions();
    expect(artifactOptions.length).toBe(1);
    await artifactOptions[0].click();

    const artifactTree = await harness.matTreeHarness();

    let artifactTreeNodes = await artifactTree.getNodes();
    expect(artifactTreeNodes.length).toBe(1);
    await artifactTreeNodes[0].expand();
    artifactTreeNodes = await artifactTree.getNodes();

    const shoppingListNode = artifactTreeNodes[0];
    expect(await shoppingListNode.getText()).toContain('Shopping List');

    const veggiesListNode = artifactTreeNodes[1];
    expect(await veggiesListNode?.getText()).toContain('Veggies');
    expect(await veggiesListNode?.getText()).toContain('Cucumber');

    const fruitsListNode = artifactTreeNodes[2];
    expect(await fruitsListNode?.getText()).toContain('Fruits');
    expect(await fruitsListNode?.getText()).toContain('Apple');
    expect(await fruitsListNode?.getText()).toContain('Banana');

    const exoticFruitsListNode = artifactTreeNodes[3];
    expect(await exoticFruitsListNode?.getText()).toContain('Exotic Fruits');
    expect(await exoticFruitsListNode?.getText()).toContain('Mango');
  }));
});
