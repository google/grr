import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CollectMultipleFilesArgs,
  DefaultFlowProgress,
} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {PluginsModule} from './module';
import {StatMultipleFilesDetails} from './stat_multiple_files_details';

initTestEnvironment();

describe('stat-multiple-files-details component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, PluginsModule],
      providers: [],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('shows file download button', () => {
    const fixture = TestBed.createComponent(StatMultipleFilesDetails);
    const args: CollectMultipleFilesArgs = {pathExpressions: ['/foo/**']};
    const progress: DefaultFlowProgress = {};

    fixture.componentInstance.flow = newFlow({
      name: 'StatMultipleFiles',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const menuItems = fixture.componentInstance.getExportMenuItems(
      fixture.componentInstance.flow,
      '' /** exportCommandPrefix can be left empty for testing purposes */,
    );
    expect(menuItems[0]).toEqual(
      fixture.componentInstance.getDownloadFilesExportMenuItem(
        fixture.componentInstance.flow,
      ),
    );
    expect(menuItems[0].url).toMatch(
      '/api/v2/clients/.+/flows/.+/results/files-archive',
    );
  });
});
