import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {CollectMultipleFilesArgs, CollectMultipleFilesProgress} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {CollectMultipleFilesDetails} from './collect_multiple_files_details';
import {PluginsModule} from './module';


initTestEnvironment();

describe('collect-multiple-files-details component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));


  it('shows file download button', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesDetails);
    const args: CollectMultipleFilesArgs = {pathExpressions: ['/foo/**']};
    const progress: CollectMultipleFilesProgress = {
      numCollected: '42',
    };

    fixture.componentInstance.flow = newFlow({
      name: 'CollectMultipleFiles',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const menuItems = fixture.componentInstance.getExportMenuItems(
        fixture.componentInstance.flow);
    expect(menuItems[0])
        .toEqual(fixture.componentInstance.getDownloadFilesExportMenuItem(
            fixture.componentInstance.flow));
    expect(menuItems[0].url)
        .toMatch('/api/v2/clients/.+/flows/.+/results/files-archive');
  });
});
