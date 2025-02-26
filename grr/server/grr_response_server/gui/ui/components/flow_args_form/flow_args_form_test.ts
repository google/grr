import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component, Input, ViewChild} from '@angular/core';
import {
  ComponentFixture,
  TestBed,
  fakeAsync,
  flush,
  tick,
  waitForAsync,
} from '@angular/core/testing';
import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ReplaySubject, Subject, firstValueFrom} from 'rxjs';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {
  ArtifactCollectorFlowArgs,
  Browser,
  CollectBrowserHistoryArgs,
  CollectFilesByKnownPathArgsCollectionLevel,
  ExecutePythonHackArgs,
  GlobComponentExplanation,
  LaunchBinaryArgs,
  ListNamedPipesFlowArgsPipeEndFilter,
  ListNamedPipesFlowArgsPipeTypeFilter,
  TimelineArgs,
} from '../../lib/api/api_interfaces';
import {ApiModule} from '../../lib/api/module';
import {
  BinaryType,
  FlowType,
  OperatingSystem,
  SourceType,
  type FlowDescriptor,
} from '../../lib/models/flow';
import {
  newArtifactDescriptorMap,
  newClient,
} from '../../lib/models/model_test_util';
import {ExplainGlobExpressionService} from '../../lib/service/explain_glob_expression_service/explain_glob_expression_service';
import {deepFreeze} from '../../lib/type_utils';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {
  ClientPageGlobalStoreMock,
  mockClientPageGlobalStore,
} from '../../store/client_page_global_store_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {
  STORE_PROVIDERS,
  injectMockStore,
} from '../../store/store_test_providers';
import {initTestEnvironment} from '../../testing';

import {FlowArgsForm} from './flow_args_form';

initTestEnvironment();

const TEST_FLOW_DESCRIPTORS = deepFreeze({
  ArtifactCollectorFlow: {
    name: FlowType.ARTIFACT_COLLECTOR_FLOW,
    friendlyName: 'Collect artifact',
    category: 'Collector',
    blockHuntCreation: false,
    defaultArgs: {
      artifactList: [],
    },
  },
  CollectBrowserHistory: {
    name: FlowType.COLLECT_BROWSER_HISTORY,
    friendlyName: 'Browser History',
    category: 'Browser',
    blockHuntCreation: false,
    defaultArgs: {
      browsers: [Browser.CHROMIUM_BASED_BROWSERS],
    },
  },
  CollectFilesByKnownPath: {
    name: FlowType.COLLECT_FILES_BY_KNOWN_PATH,
    friendlyName: 'Collect Files based on their absolute path',
    category: 'Filesystem',
    blockHuntCreation: false,
    defaultArgs: {
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
      paths: [],
    },
  },
  CollectLargeFileFlow: {
    name: FlowType.COLLECT_LARGE_FILE_FLOW,
    friendlyName: 'Collect Large File',
    category: 'Filesystem',
    blockHuntCreation: true,
    defaultArgs: {
      pathSpec: {},
      signedUrl: '',
    },
  },
  CollectMultipleFiles: {
    name: FlowType.COLLECT_MULTIPLE_FILES,
    friendlyName: 'Collect Multiple Files',
    category: 'Filesystem',
    blockHuntCreation: false,
    defaultArgs: {
      pathExpressions: [],
    },
  },
  ListDirectory: {
    name: FlowType.LIST_DIRECTORY,
    friendlyName: 'List Directory',
    category: 'Filesystem',
    blockHuntCreation: false,
    defaultArgs: {
      pathSpec: {},
    },
  },
  ListNamedPipes: {
    name: FlowType.LIST_NAMED_PIPES_FLOW,
    friendlyName: 'List named pipes',
    category: 'Processes',
    blockHuntCreation: false,
    defaultArgs: {
      pipeNameRegex: '',
      procExeRegex: '',
      pipeTypeFilter: ListNamedPipesFlowArgsPipeTypeFilter.ANY_TYPE,
      pipeEndFilter: ListNamedPipesFlowArgsPipeEndFilter.ANY_END,
    },
  },
  ListProcesses: {
    name: FlowType.LIST_PROCESSES,
    friendlyName: 'List processes',
    category: 'Processes',
    blockHuntCreation: false,
    defaultArgs: {
      filenameRegex: '/(default)foo)/',
      pids: [12222234, 456],
      connectionStates: [],
      fetchBinaries: false,
    },
  },
  Netstat: {
    name: FlowType.NETSTAT,
    friendlyName: 'List active network connections on a system.',
    category: 'Network',
    blockHuntCreation: false,
    defaultArgs: {
      listeningOnly: false,
    },
  },
  ReadLowLevel: {
    name: FlowType.READ_LOW_LEVEL,
    friendlyName: 'Read device low level',
    category: 'Filesystem',
    blockHuntCreation: false,
    defaultArgs: {},
  },
  TimelineFlow: {
    name: FlowType.TIMELINE_FLOW,
    friendlyName: 'Collect path timeline',
    category: 'Filesystem',
    blockHuntCreation: false,
    defaultArgs: {},
  },
  ExecutePythonHack: {
    name: FlowType.EXECUTE_PYTHON_HACK,
    friendlyName: 'Execute Python Hack',
    category: 'Administrative',
    blockHuntCreation: false,
    defaultArgs: {
      hackName: '',
    },
  },
  LaunchBinary: {
    name: FlowType.LAUNCH_BINARY,
    friendlyName: 'Launch Binary',
    category: 'Administrative',
    blockHuntCreation: false,
    defaultArgs: {
      binary: '',
    },
  },
  OnlineNotification: {
    name: FlowType.ONLINE_NOTIFICATION,
    friendlyName: 'Online Notification',
    category: 'Administrative',
    blockHuntCreation: false,
    defaultArgs: {
      email: 'foo@bar.com',
    },
  },
  DumpProcessMemory: {
    name: FlowType.DUMP_PROCESS_MEMORY,
    friendlyName: 'Dump Process Memory',
    category: 'Memory',
    blockHuntCreation: false,
    defaultArgs: {},
  },
  YaraProcessScan: {
    name: FlowType.YARA_PROCESS_SCAN,
    friendlyName: 'Yara Process Scan',
    category: 'Memory',
    blockHuntCreation: false,
    defaultArgs: {},
  },
});

@Component({
  standalone: false,
  template:
    '<flow-args-form [flowDescriptor]="flowDescriptor"></flow-args-form>',
  jit: true,
})
class TestHostComponent {
  @Input() flowDescriptor?: FlowDescriptor;
  @ViewChild(FlowArgsForm) flowArgsForm!: FlowArgsForm;
}

function setUp() {
  return TestBed.configureTestingModule({
    imports: [NoopAnimationsModule, ApiModule, FlowArgsFormModule],
    declarations: [TestHostComponent],
    providers: [...STORE_PROVIDERS],
    teardown: {destroyAfterEach: false},
  }).compileComponents();
}

describe('FlowArgsForm Component', () => {
  beforeEach(waitForAsync(() => {
    setUp();
  }));

  it('is empty initially', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText.trim()).toEqual('');
  });

  it('renders sub-form correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.CollectBrowserHistory;
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Chromium');
  });

  it('emits form value changes', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.CollectBrowserHistory;
    fixture.detectChanges();

    const initialArgs = (await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    )) as CollectBrowserHistoryArgs;
    expect(initialArgs.browsers ?? []).toContain(
      Browser.CHROMIUM_BASED_BROWSERS,
    );

    // This test assumes that the first label in the CollectBrowserHistoryForm
    // is Chromium Based Browsers, which is not ideal, but an effective workaround.
    const label = fixture.debugElement.query(By.css('label')).nativeElement;
    expect(label.innerText).toContain('Chromium');
    label.click();
    fixture.detectChanges();

    const args = (await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    )) as CollectBrowserHistoryArgs;
    expect(args.browsers ?? []).not.toContain(Browser.CHROMIUM_BASED_BROWSERS);
  });

  it('is empty after flow unselection', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.CollectBrowserHistory;
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor = undefined;
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText.trim()).toEqual('');
  });

  it('emits INVALID when form input is invalid', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.ReadLowLevel;
    fixture.detectChanges();

    const byteInput = fixture.debugElement.query(By.css('input[byteInput]'));
    byteInput.nativeElement.value = 'invalid';
    byteInput.triggerEventHandler('change', {target: byteInput.nativeElement});
    fixture.detectChanges();

    expect(
      await firstValueFrom(fixture.componentInstance.flowArgsForm.valid$),
    ).toBeFalse();
  });
});

for (const fd of Object.values(TEST_FLOW_DESCRIPTORS)) {
  describe(`FlowArgForm ${fd.name}`, () => {
    beforeEach(waitForAsync(() => {
      setUp();
    }));

    it('renders a sub-form', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();

      fixture.componentInstance.flowDescriptor = fd;
      fixture.detectChanges();

      expect(fixture.nativeElement.innerText.trim()).toBeTruthy();
    });

    it('emits initial form values', waitForAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();

      fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
        (values) => {
          expect(values).toBeTruthy();
        },
      );

      fixture.componentInstance.flowDescriptor = fd;
      fixture.detectChanges();
    }));

    it('focusses a child element when autofocus is set ', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();
      fixture.componentInstance.flowDescriptor = fd;
      fixture.componentInstance.flowArgsForm.autofocus = true;
      fixture.detectChanges();

      const focussedElement = document.activeElement;
      expect(focussedElement).not.toBeNull();
      expect(
        fixture.debugElement.nativeElement.contains(focussedElement),
      ).toBeTrue();
    });

    it('does NOT focus a child element when autofocus is unset', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();
      fixture.componentInstance.flowDescriptor = fd;
      fixture.detectChanges();

      expect(
        fixture.debugElement.nativeElement.contains(document.activeElement),
      ).toBeFalse();
    });
  });
}

describe(`FlowArgForm CollectMultipleFiles`, () => {
  let clientPageGlobalStore: ClientPageGlobalStoreMock;
  let explainGlobExpressionService: Partial<ExplainGlobExpressionService>;
  let explanation$: Subject<readonly GlobComponentExplanation[]>;

  beforeEach(waitForAsync(() => {
    clientPageGlobalStore = mockClientPageGlobalStore();
    explanation$ = new ReplaySubject(1);
    explainGlobExpressionService = {
      explanation$,
      explain: jasmine.createSpy('explain'),
    };
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ApiModule, FlowArgsFormModule],
      declarations: [TestHostComponent],
      providers: [
        {
          provide: ClientPageGlobalStore,
          useFactory: () => clientPageGlobalStore,
        },
      ],
      teardown: {destroyAfterEach: false},
    })
      // Override ALL providers, because each path expression input provides
      // its own ExplainGlobExpressionService. The above way only overrides
      // the root-level.
      .overrideProvider(ExplainGlobExpressionService, {
        useFactory: () => explainGlobExpressionService,
      })
      .compileComponents();
  }));

  function prepareFixture() {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    clientPageGlobalStore.mockedObservables.selectedClient$.next(
      newClient({
        clientId: 'C.1234',
      }),
    );

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.CollectMultipleFiles;
    fixture.detectChanges();

    return fixture;
  }

  it('calls the GlobalStore to explain GlobExpressions', fakeAsync(() => {
    const fixture = prepareFixture();

    const input = fixture.debugElement.query(By.css('input')).nativeElement;
    input.value = '/home/{foo,bar}';
    input.dispatchEvent(new Event('input'));

    tick(1000);
    fixture.detectChanges();

    expect(explainGlobExpressionService.explain).toHaveBeenCalledWith(
      'C.1234',
      '/home/{foo,bar}',
    );
  }));

  it('shows the loaded GlobExpressionExplanation', () => {
    const fixture = prepareFixture();

    explanation$.next([
      {globExpression: '/home/'},
      {globExpression: '{foo,bar}', examples: ['foo', 'bar']},
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.innerText;
    expect(text).toContain('/home/foo');
  });

  it('allows adding path expressions', waitForAsync(() => {
    const fixture = prepareFixture();

    let inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(1);

    const addButton = fixture.debugElement.query(
      By.css('#button-add-path-expression'),
    );
    addButton.nativeElement.click();
    fixture.detectChanges();

    inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(2);

    inputs[0].nativeElement.value = '/0';
    inputs[0].nativeElement.dispatchEvent(new Event('input'));

    inputs[1].nativeElement.value = '/1';
    inputs[1].nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
      (values) => {
        expect(values).toEqual({pathExpressions: ['/0', '/1']});
      },
    );
  }));

  it('allows removing path expressions', waitForAsync(() => {
    const fixture = prepareFixture();

    let inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(1);

    const addButton = fixture.debugElement.query(
      By.css('#button-add-path-expression'),
    );
    addButton.nativeElement.click();
    fixture.detectChanges();

    inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(2);

    inputs[0].nativeElement.value = '/0';
    inputs[0].nativeElement.dispatchEvent(new Event('input'));

    inputs[1].nativeElement.value = '/1';
    inputs[1].nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const removeButtons = fixture.debugElement.queryAll(
      By.css("button[aria-label='Remove']"),
    );
    expect(removeButtons.length).toEqual(2);

    removeButtons[1].nativeElement.click();
    fixture.detectChanges();

    inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(1);

    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
      (values) => {
        expect(values).toEqual({pathExpressions: ['/0']});
      },
    );
  }));

  it('allows adding modification time expression', () => {
    const fixture = prepareFixture();

    expect(
      fixture.debugElement.queryAll(By.css('time-range-condition')),
    ).toHaveSize(0);

    const conditionButton = fixture.debugElement.query(
      By.css('button[name=modificationTime]'),
    );
    conditionButton.nativeElement.click();
    fixture.detectChanges();

    // The button should disappear after the click.
    expect(
      fixture.debugElement.queryAll(By.css('button[name=modificationTime]')),
    ).toHaveSize(0);
    expect(
      fixture.debugElement.queryAll(By.css('time-range-condition')),
    ).toHaveSize(1);
  });

  it('allows removing modification time expression', () => {
    const fixture = prepareFixture();

    const conditionButton = fixture.debugElement.query(
      By.css('button[name=modificationTime]'),
    );
    conditionButton.nativeElement.click();
    fixture.detectChanges();

    // The form should now appear.
    expect(
      fixture.debugElement.queryAll(By.css('time-range-condition')),
    ).toHaveSize(1);

    const removeButton = fixture.debugElement.query(
      By.css('.header .remove button'),
    );
    removeButton.nativeElement.click();
    fixture.detectChanges();

    // The form should now disappear.
    expect(
      fixture.debugElement.queryAll(By.css('time-range-condition')),
    ).toHaveSize(0);
  });
});

describe(`FlowArgForm ArtifactCollectorFlowForm`, () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ApiModule, FlowArgsFormModule],
      declarations: [TestHostComponent],
      providers: [...STORE_PROVIDERS],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  function prepareFixture() {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.ArtifactCollectorFlow;
    fixture.detectChanges();

    return {fixture};
  }

  it('shows initial artifact suggestions', fakeAsync(async () => {
    const {fixture} = prepareFixture();

    injectMockStore(
      ConfigGlobalStore,
    ).mockedObservables.artifactDescriptors$.next(
      newArtifactDescriptorMap([
        {
          name: 'foo',
          sources: [
            {
              type: SourceType.FILE,
              paths: ['/sample/path'],
              conditions: [],
              supportedOs: new Set(),
            },
          ],
        },
        {name: 'bar', doc: 'description123'},
        {name: 'baz'},
      ]),
    );

    fixture.detectChanges();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );
    await autocompleteHarness.focus();
    const options = await autocompleteHarness.getOptions();
    expect(options.length).toEqual(3);

    const texts = await Promise.all(options.map((o) => o.getText()));
    expect(texts[0]).toContain('foo');
    expect(texts[0]).toContain('/sample/path');
    expect(texts[1]).toContain('bar');
    expect(texts[1]).toContain('description123');
    expect(texts[2]).toContain('baz');
  }));

  it('filters artifact suggestions based on user input', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(
      ConfigGlobalStore,
    ).mockedObservables.artifactDescriptors$.next(
      newArtifactDescriptorMap([{name: 'foo'}, {name: 'baar'}, {name: 'baaz'}]),
    );

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );
    await autocompleteHarness.enterText('aa');
    const options = await autocompleteHarness.getOptions();
    expect(options.length).toEqual(2);

    const texts = await Promise.all(options.map((o) => o.getText()));
    expect(texts[0]).toContain('baar');
    expect(texts[1]).toContain('baaz');
  });

  it('searches artifact fields based on user input', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(
      ConfigGlobalStore,
    ).mockedObservables.artifactDescriptors$.next(
      newArtifactDescriptorMap([
        {
          name: 'foo',
          sources: [
            {
              type: SourceType.FILE,
              paths: ['/sample/path'],
              conditions: [],
              supportedOs: new Set(),
            },
          ],
        },
        {name: 'bar'},
        {name: 'baz'},
      ]),
    );

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );
    await autocompleteHarness.enterText('SaMpLe');
    const options = await autocompleteHarness.getOptions();
    expect(options.length).toEqual(1);
    expect(await options[0].getText()).toContain('foo');
  });

  it('configures flow args with selected artifact suggestion', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(
      ConfigGlobalStore,
    ).mockedObservables.artifactDescriptors$.next(
      newArtifactDescriptorMap([{name: 'foo'}, {name: 'bar'}, {name: 'baz'}]),
    );

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );
    await autocompleteHarness.selectOption({text: /bar/});

    const flowArgValues = (await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    )) as ArtifactCollectorFlowArgs;
    expect(flowArgValues.artifactList).toEqual(['bar']);
  });

  it('marks artifacts for different operating system as unavailable', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(
      ConfigGlobalStore,
    ).mockedObservables.artifactDescriptors$.next(
      newArtifactDescriptorMap([
        {name: 'foo', supportedOs: new Set([OperatingSystem.DARWIN])},
        {name: 'bar', supportedOs: new Set([OperatingSystem.WINDOWS])},
        {
          name: 'baz',
          supportedOs: new Set([OperatingSystem.DARWIN, OperatingSystem.LINUX]),
        },
      ]),
    );
    injectMockStore(
      ClientPageGlobalStore,
    ).mockedObservables.selectedClient$.next(
      newClient({knowledgeBase: {os: 'Darwin'}}),
    );
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );
    await autocompleteHarness.focus();
    const options = await autocompleteHarness.getOptions();
    // Unavailable artifacts should still be shown for discoverability.
    expect(options.length).toEqual(3);

    const elements = await Promise.all(options.map((o) => o.host()));
    expect(await elements[0].hasClass('unavailable')).toBeFalse();
    expect(await elements[1].hasClass('unavailable')).toBeTrue();
    expect(await elements[2].hasClass('unavailable')).toBeFalse();

    expect(await options[1].getText()).toContain('Windows');
  });

  it('previews sources for the selected artifact', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(
      ConfigGlobalStore,
    ).mockedObservables.artifactDescriptors$.next(
      newArtifactDescriptorMap([
        {
          name: 'foo',
          sources: [
            {
              type: SourceType.ARTIFACT_GROUP,
              names: ['bar'],
              conditions: [],
              supportedOs: new Set(),
            },
          ],
        },
        {
          name: 'bar',
          sources: [
            {
              type: SourceType.REGISTRY_KEY,
              keys: ['HKLM'],
              conditions: [],
              supportedOs: new Set(),
            },
          ],
        },
      ]),
    );

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );
    await autocompleteHarness.selectOption({text: /foo/});

    const text = fixture.nativeElement.innerText;
    // Validate that foo's child artifact and all its sources are shown.
    expect(text).toContain('bar');
    expect(text).toContain('Collects Windows Registry key');
    expect(text).toContain('HKLM');
  });
});

describe(`FlowArgForm ListProcesses`, () => {
  beforeEach(waitForAsync(() => {
    setUp();
  }));
  it('emits form input values', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.ListProcesses;
    fixture.detectChanges();

    await setInputValue(fixture, 'input[name=filenameRegex]', '/foo/');
    await setInputValue(fixture, 'input[name=pids]', '123, 456');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );
    await autocompleteHarness.selectOption({text: 'CLOSING'});

    const checkboxHarness = await harnessLoader.getHarness(MatCheckboxHarness);
    await checkboxHarness.check();

    const values = await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    );

    expect(values).toEqual({
      pids: [123, 456],
      filenameRegex: '/foo/',
      connectionStates: ['CLOSING'],
      fetchBinaries: true,
    });
  });

  it('flags non-numeric pids as invalid', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.ListProcesses;
    fixture.detectChanges();

    await setInputValue(fixture, 'input[name=pids]', '12notnumeric3');

    expect(
      await firstValueFrom(fixture.componentInstance.flowArgsForm.valid$),
    ).toBeFalse();
  });
});

async function setInputValue(
  fixture: ComponentFixture<unknown>,
  query: string,
  value: string,
) {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const inputHarness = await harnessLoader.getHarness(
    MatInputHarness.with({selector: query}),
  );
  await inputHarness.setValue(value);
}

describe(`FlowArgForm ExecutePythonHackForm`, () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ApiModule, FlowArgsFormModule],
      declarations: [TestHostComponent],
      providers: [...STORE_PROVIDERS],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  });

  function prepareFixture() {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.ExecutePythonHack;
    fixture.detectChanges();

    return {fixture};
  }

  it('shows initial python hack suggestions', fakeAsync(async () => {
    const {fixture} = prepareFixture();

    injectMockStore(ConfigGlobalStore).mockedObservables.binaries$.next([
      {
        type: BinaryType.PYTHON_HACK,
        path: 'windows/hello.py',
        size: BigInt(1),
        timestamp: new Date(1),
      },
      {
        type: BinaryType.PYTHON_HACK,
        path: 'linux/foo.py',
        size: BigInt(1),
        timestamp: new Date(1),
      },
      {
        type: BinaryType.EXECUTABLE,
        path: 'windows/executable.exe',
        size: BigInt(1),
        timestamp: new Date(1),
      },
    ]);

    fixture.detectChanges();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );

    await autocompleteHarness.focus();

    const options = await autocompleteHarness.getOptions();
    expect(options.length).toEqual(2);

    const texts = await Promise.all(options.map((o) => o.getText()));
    expect(texts[0]).toEqual('linux/foo.py');
    expect(texts[1]).toEqual('windows/hello.py');
  }));

  it('filters suggestions based on user input', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(ConfigGlobalStore).mockedObservables.binaries$.next([
      {
        type: BinaryType.PYTHON_HACK,
        path: 'windows/hello.py',
        size: BigInt(1),
        timestamp: new Date(1),
      },
      {
        type: BinaryType.PYTHON_HACK,
        path: 'linux/foo.py',
        size: BigInt(1),
        timestamp: new Date(1),
      },
    ]);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );

    await autocompleteHarness.enterText('fo');

    fixture.detectChanges();

    const options = await autocompleteHarness.getOptions();
    expect(options.length).toEqual(1);

    const texts = await Promise.all(options.map((o) => o.getText()));
    expect(texts[0]).toEqual('linux/foo.py');
  });

  it('configures flow args with selected hack suggestion', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(ConfigGlobalStore).mockedObservables.binaries$.next([
      {
        type: BinaryType.PYTHON_HACK,
        path: 'windows/hello.py',
        size: BigInt(1),
        timestamp: new Date(1),
      },
      {
        type: BinaryType.PYTHON_HACK,
        path: 'linux/foo.py',
        size: BigInt(1),
        timestamp: new Date(1),
      },
    ]);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );

    await autocompleteHarness.selectOption({text: /foo/});

    const flowArgValues = (await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    )) as ExecutePythonHackArgs;
    expect(flowArgValues.hackName).toEqual('linux/foo.py');
  });

  it('allows adding arguments', async () => {
    const {fixture} = prepareFixture();

    const getArgs = () =>
      firstValueFrom(
        fixture.componentInstance.flowArgsForm.flowArgValues$,
      ) as Promise<ExecutePythonHackArgs>;

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const buttonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: 'Add argument'}),
    );

    expect((await getArgs()).pyArgs ?? {}).toEqual({});

    await buttonHarness.click();
    await buttonHarness.click();

    const inputs = await harnessLoader.getAllHarnesses(
      MatInputHarness.with({ancestor: '.key-value-group'}),
    );
    await inputs[0].setValue('key1');
    await inputs[1].setValue('val1');
    await inputs[2].setValue('key2');
    await inputs[3].setValue('val2');

    expect((await getArgs()).pyArgs).toEqual({
      dat: [
        {k: {string: 'key1'}, v: {string: 'val1'}},
        {k: {string: 'key2'}, v: {string: 'val2'}},
      ],
    });
  });

  it('allows removing arguments', async () => {
    const {fixture} = prepareFixture();

    const getArgs = () =>
      firstValueFrom(
        fixture.componentInstance.flowArgsForm.flowArgValues$,
      ) as Promise<ExecutePythonHackArgs>;

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const buttonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: 'Add argument'}),
    );

    await buttonHarness.click();
    await buttonHarness.click();

    const inputs = await harnessLoader.getAllHarnesses(
      MatInputHarness.with({ancestor: '.key-value-group'}),
    );
    await inputs[0].setValue('key1');
    await inputs[1].setValue('val1');
    await inputs[2].setValue('key2');
    await inputs[3].setValue('val2');

    const removeButton = await harnessLoader.getHarness(
      MatButtonHarness.with({selector: '.remove-button'}),
    );
    await removeButton.click();

    expect((await getArgs()).pyArgs).toEqual({
      dat: [{k: {string: 'key2'}, v: {string: 'val2'}}],
    });
  });
});

describe(`FlowArgForm LaunchBinary`, () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ApiModule, FlowArgsFormModule],
      declarations: [TestHostComponent],
      providers: [...STORE_PROVIDERS],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  function prepareFixture() {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.LaunchBinary;
    fixture.detectChanges();

    return {fixture};
  }

  it('shows initial suggestions', fakeAsync(async () => {
    const {fixture} = prepareFixture();

    injectMockStore(ConfigGlobalStore).mockedObservables.binaries$.next([
      {
        type: BinaryType.EXECUTABLE,
        path: 'windows/hello.exe',
        size: BigInt(1),
        timestamp: new Date(1),
      },
      {
        type: BinaryType.EXECUTABLE,
        path: 'linux/foo.sh',
        size: BigInt(1),
        timestamp: new Date(1),
      },
      {
        type: BinaryType.PYTHON_HACK,
        path: 'windows/py.py',
        size: BigInt(1),
        timestamp: new Date(1),
      },
    ]);

    fixture.detectChanges();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );

    await autocompleteHarness.focus();

    const options = await autocompleteHarness.getOptions();
    expect(options.length).toEqual(2);

    const texts = await Promise.all(options.map((o) => o.getText()));
    expect(texts[0]).toContain('linux/foo.sh');
    expect(texts[1]).toContain('windows/hello.exe');
  }));

  it('filters suggestions based on user input', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(ConfigGlobalStore).mockedObservables.binaries$.next([
      {
        type: BinaryType.EXECUTABLE,
        path: 'windows/hello.exe',
        size: BigInt(1),
        timestamp: new Date(1),
      },
      {
        type: BinaryType.EXECUTABLE,
        path: 'linux/foo.sh',
        size: BigInt(1),
        timestamp: new Date(1),
      },
    ]);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );

    await autocompleteHarness.enterText('fo');

    fixture.detectChanges();

    const options = await autocompleteHarness.getOptions();
    expect(options.length).toEqual(1);

    const texts = await Promise.all(options.map((o) => o.getText()));
    expect(texts[0]).toContain('linux/foo.sh');
  });

  it('configures flow args with selected suggestion and required aff4 prefix', async () => {
    const {fixture} = prepareFixture();

    injectMockStore(ConfigGlobalStore).mockedObservables.binaries$.next([
      {
        type: BinaryType.EXECUTABLE,
        path: 'windows/hello.exe',
        size: BigInt(1),
        timestamp: new Date(1),
      },
      {
        type: BinaryType.EXECUTABLE,
        path: 'linux/foo.sh',
        size: BigInt(1),
        timestamp: new Date(1),
      },
    ]);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const autocompleteHarness = await harnessLoader.getHarness(
      MatAutocompleteHarness,
    );

    await autocompleteHarness.selectOption({text: /foo/});

    const flowArgValues = (await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    )) as LaunchBinaryArgs;
    expect(flowArgValues.binary).toEqual(
      'aff4:/config/executables/linux/foo.sh',
    );
  });
});

describe(`FlowArgForm TimelineFlow`, () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ApiModule, FlowArgsFormModule],
      declarations: [TestHostComponent],
      providers: [...STORE_PROVIDERS],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  function prepareFixture() {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
      TEST_FLOW_DESCRIPTORS.TimelineFlow;
    fixture.detectChanges();

    return {fixture};
  }

  it('converts entered data to base64-bytes', fakeAsync(async () => {
    const {fixture} = prepareFixture();

    await setInputValue(fixture, 'input[name=root]', '/foo/bar');

    const flowArgValues = (await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    )) as TimelineArgs;
    expect(flowArgValues.root).toEqual('L2Zvby9iYXI=');
  }));

  it('decodes provided path with base64', fakeAsync(async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.flowDescriptor = {
      ...TEST_FLOW_DESCRIPTORS.TimelineFlow,
      defaultArgs: {root: 'L2Zvby9iYXI='},
    };
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('input[name=root]')).nativeElement
        .value,
    ).toEqual('/foo/bar');

    const flowArgValues = (await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    )) as TimelineArgs;
    expect(flowArgValues.root).toEqual('L2Zvby9iYXI=');

    /* We need to flush due to getting the following error otherwise:

       `Error: 1 timer(s) still in the queue`

       This happens due to MatFormFieldFloatingLabel running the
       following:

       `setTimeout(() => this._parent._handleLabelResized());`

       When TimelineForm component gets rendered, as we autofocus the Input
       component through FlowArgumentForm Component.
       */
    flush();
  }));

  it('emits the empty string for empty root path', fakeAsync(async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.flowDescriptor = {
      ...TEST_FLOW_DESCRIPTORS.TimelineFlow,
      defaultArgs: {root: ''},
    };
    fixture.detectChanges();

    const flowArgValues = (await firstValueFrom(
      fixture.componentInstance.flowArgsForm.flowArgValues$,
    )) as TimelineArgs;
    expect(flowArgValues.root).toEqual('');
  }));
});
