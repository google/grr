import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {Browser} from '../../../lib/api/api_interfaces';
import {getFlowTitleFromFlowName} from '../../../lib/models/flow';
import {
  newFlowDescriptorMap,
  newHunt,
} from '../../../lib/models/model_test_util';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {
  ConfigGlobalStoreMock,
  mockConfigGlobalStore,
} from '../../../store/config_global_store_test_util';
import {getActivatedChildRoute, initTestEnvironment} from '../../../testing';

import {HuntFlowArguments} from './hunt_flow_arguments';

// TODO: Refactor form helper into common `form_testing.ts` file.
// For unknown reasons (likely related to some injection) we cannot use the
// following helper function which is also defined in `form_testing.ts`. Thus,
// we copy it over here to be able to easily check the component values.
async function getCheckboxValue(
  fixture: ComponentFixture<unknown>,
  query: string,
): Promise<boolean> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const checkboxHarness = await harnessLoader.getHarness(
    MatCheckboxHarness.with({selector: query}),
  );
  return await checkboxHarness.isChecked();
}

initTestEnvironment();

@Component({
  template: '<hunt-flow-arguments [hunt]="hunt"></hunt-flow-arguments>',
})
class TestHostComponent {
  hunt = newHunt({});
}

describe('HuntFlowArguments test', () => {
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(async () => {
    configGlobalStore = mockConfigGlobalStore();

    await TestBed.configureTestingModule({
      imports: [RouterTestingModule, NoopAnimationsModule, HuntFlowArguments],
      declarations: [TestHostComponent],
      providers: [
        {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
        {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  });

  it('With flowDescriptor with link', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const flowName = 'CollectBrowserHistory';
    fixture.componentInstance.hunt = newHunt({
      flowReference: {clientId: 'C1234', flowId: 'F5678'},
      flowName,
      flowArgs: {
        '@type':
          'type.googleapis.com/grr.CollectBrowserHistoryArgs',
        'browsers': [Browser.CHROME],
      },
    });
    fixture.detectChanges();
    configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap({
        name: flowName,
        friendlyName: 'Browser History',
      }),
    );
    fixture.detectChanges();

    expect(fixture.nativeElement).toBeTruthy();
    const flowLink = fixture.debugElement.query(By.css('.header a'));
    expect(flowLink.attributes['href']).toContain('clients/C1234/flows/F5678');
    expect(flowLink.nativeElement.textContent).toContain(
      getFlowTitleFromFlowName(flowName),
    );

    const flowID = fixture.debugElement.query(
      By.css('.header app-copy-button'),
    );
    expect(flowID.nativeElement.textContent).toContain('F5678');

    const accordion = fixture.debugElement.query(By.css('result-accordion'));
    expect(accordion.nativeElement.textContent).toContain('Flow arguments');

    const flowArgs = fixture.debugElement.query(By.css('app-flow-args-view'));
    expect(flowArgs.nativeElement).toBeTruthy();

    expect(flowArgs.nativeElement.textContent).toContain('Chrome');
    expect(await getCheckboxValue(fixture, '[name=collectChrome]')).toBeTrue();
    expect(flowArgs.nativeElement.textContent).toContain('Opera');
    expect(await getCheckboxValue(fixture, '[name=collectOpera]')).toBeFalse();
    expect(flowArgs.nativeElement.textContent).toContain('Internet Explorer');
    expect(
      await getCheckboxValue(fixture, '[name=collectInternetExplorer]'),
    ).toBeFalse();
    expect(flowArgs.nativeElement.textContent).toContain('Opera');
    expect(await getCheckboxValue(fixture, '[name=collectOpera]')).toBeFalse();
    expect(flowArgs.nativeElement.textContent).toContain('Safari');
    expect(await getCheckboxValue(fixture, '[name=collectSafari]')).toBeFalse();
  });

  it('With flowDescriptor WITHOUT link', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const flowName = 'CollectBrowserHistory';
    fixture.componentInstance.hunt = newHunt({
      flowName,
      flowArgs: {
        '@type':
          'type.googleapis.com/grr.CollectBrowserHistoryArgs',
        'browsers': [Browser.CHROME],
      },
    });
    fixture.detectChanges();
    configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap({
        name: flowName,
        friendlyName: 'Browser History',
      }),
    );
    fixture.detectChanges();

    expect(fixture.nativeElement).toBeTruthy();
    const header = fixture.debugElement.query(By.css('.header'));
    expect(header.nativeElement.textContent).toContain(
      getFlowTitleFromFlowName(flowName),
    );
  });

  it('WITHOUT flowDescriptor', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const flowName = 'CollectBrowserHistory';
    fixture.componentInstance.hunt = newHunt({
      flowReference: {clientId: 'C1234', flowId: 'F5678'},
      flowName,
      flowArgs: {
        '@type':
          'type.googleapis.com/grr.CollectBrowserHistoryArgs',
        'browsers': [Browser.CHROME],
      },
    });

    fixture.detectChanges();

    expect(fixture.nativeElement).toBeTruthy();
    const flowLink = fixture.debugElement.query(By.css('.header a'));
    expect(flowLink.attributes['href']).toContain('clients/C1234/flows/F5678');
    expect(flowLink.nativeElement.textContent).toContain(
      getFlowTitleFromFlowName(flowName),
    );

    const flowID = fixture.debugElement.query(
      By.css('.header app-copy-button'),
    );
    expect(flowID.nativeElement.textContent).toContain('F5678');

    const flowArgs = fixture.debugElement.query(By.css('app-flow-args-view'));
    expect(flowArgs).toBeFalsy();
  });
});
