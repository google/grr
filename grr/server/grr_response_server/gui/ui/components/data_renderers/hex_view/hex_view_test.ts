import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {HexViewModule} from './hex_view_module';


initTestEnvironment();

describe('HexView Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HexViewModule,
          ],
          providers: [

          ],

        })
        .compileComponents();
  }));
});
