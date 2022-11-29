import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {ProcessView} from './process_view';


initTestEnvironment();

describe('ProcessView component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ProcessView,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('displays process results', async () => {
    const fixture = TestBed.createComponent(ProcessView);
    fixture.componentInstance.data = [{pid: 0, cmdline: ['/foo', 'bar']}];
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('/foo');
  });
});
