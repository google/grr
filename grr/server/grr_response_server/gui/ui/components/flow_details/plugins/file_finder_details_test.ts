import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FileFinderActionAction, FileFinderArgs} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {FileFinderDetails} from './file_finder_details';
import {PluginsModule} from './module';


initTestEnvironment();

describe('file-finder-details component', () => {
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

  it('shows file download button if action is DOWNLOAD', () => {
    const fixture = TestBed.createComponent(FileFinderDetails);
    const args: FileFinderArgs = {
      paths: ['/foo/**'],
      action: {actionType: FileFinderActionAction.DOWNLOAD},
    };

    fixture.componentInstance.flow = newFlow({
      name: 'FileFinder',
      args,
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
