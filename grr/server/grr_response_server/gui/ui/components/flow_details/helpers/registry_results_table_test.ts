import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatTableHarness} from '@angular/material/table/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RegistryType} from '@app/lib/api/api_interfaces';
import {initTestEnvironment} from '@app/testing';

import {RegistryKey, RegistryValue} from '../../../lib/models/flow';

import {HelpersModule} from './module';



initTestEnvironment();

@Component({
  template: `
    <registry-results-table
        [results]="results"
        [totalCount]="totalCount"
        (loadMore)="loadMoreTriggered()">
    </registry-results-table>`
})
class TestHostComponent {
  results?: ReadonlyArray<RegistryKey|RegistryValue>;
  totalCount?: number;

  loadMoreTriggered = jasmine.createSpy('loadMoreTriggered');
}

describe('RegistryResultsTable Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
          ],
          declarations: [
            TestHostComponent,
          ],

          providers: []
        })
        .compileComponents();
  }));

  it('renders the path (and type) of RegistryKeys', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.results = [
      {path: 'HKLM\\reg0', type: 'REG_KEY'},
      {path: 'HKLM\\reg1', type: 'REG_KEY'},
    ];

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTableHarness);
    const contents = await harness.getCellTextByColumnName();

    expect(contents['path'].text[0]).toContain('HKLM\\reg0');
    expect(contents['path'].text[1]).toContain('HKLM\\reg1');
    expect(contents['type'].text[0]).toEqual('REG_KEY');
    expect(contents['type'].text[1]).toEqual('REG_KEY');
  });

  it('renders the path, type, size of RegistryValues', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.results = [
      {path: 'HKLM\\reg0', type: RegistryType.REG_NONE, size: BigInt(0)},
      {path: 'HKLM\\reg1', type: RegistryType.REG_BINARY, size: BigInt(123)},
    ];

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTableHarness);
    const contents = await harness.getCellTextByColumnName();

    expect(contents['path'].text[0]).toContain('HKLM\\reg0');
    expect(contents['path'].text[1]).toContain('HKLM\\reg1');
    expect(contents['type'].text[0]).toEqual('REG_NONE');
    expect(contents['type'].text[1]).toEqual('REG_BINARY');
    expect(contents['size'].text[0]).toContain('0');
    expect(contents['size'].text[1]).toContain('123');
  });

  it('emits an event when "load more" is clicked', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.results = [];
    fixture.componentInstance.totalCount = 2;
    fixture.detectChanges();

    expect(fixture.componentInstance.loadMoreTriggered).not.toHaveBeenCalled();

    const button = fixture.nativeElement.querySelector('button.load-more');
    button.click();

    expect(fixture.componentInstance.loadMoreTriggered).toHaveBeenCalled();
  });
});
