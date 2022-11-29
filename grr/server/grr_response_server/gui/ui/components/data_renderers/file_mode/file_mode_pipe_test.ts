import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {FileModeModule} from './file_mode_module';


@Component({template: '{{ value | fileMode }}'})
class TestHostComponent {
  value: string|undefined;
}

initTestEnvironment();

describe('FileResultTable render()', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FileModeModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  function render(value?: string) {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.value = value;
    fixture.detectChanges();
    return fixture.nativeElement.innerText.trim();
  }

  it('produces - when value is undefined', () => {
    expect(render(undefined)).toBe('-');
  });

  it('correctly handles regular files', () => {
    const mode = render('33188');
    expect(mode).toBe('-rw-r--r--');
  });

  it('correctly handles directories', () => {
    const mode = render('16832');
    expect(mode).toBe('drwx------');
  });

  it('correctly handles character devices', () => {
    const mode = render('8592');
    expect(mode).toBe('crw--w----');
  });

  it('correctly handles symbolic links', () => {
    const mode = render('41325');
    expect(mode).toBe('lr-xr-xr-x');
  });

  it('correctly handles block devices', () => {
    const mode = render('24960');
    expect(mode).toBe('brw-------');
  });

  it('correctly handles FIFO pipes', () => {
    const mode = render('4516');
    expect(mode).toBe('prw-r--r--');
  });

  it('correctly handles sockets', () => {
    const mode = render('50668');
    expect(mode).toBe('srwxr-sr--');
  });

  it('considers the S_ISUID flag', () => {
    let mode = render('35300');
    expect(mode).toBe('-rwsr--r--');

    mode = render('35236');
    expect(mode).toBe('-rwSr--r--');
  });

  it('considers the S_ISGID flag', () => {
    let mode = render('36332');
    expect(mode).toBe('-rwsr-sr--');

    mode = render('36324');
    expect(mode).toBe('-rwsr-Sr--');
  });

  it('considers the S_ISVTX flag', () => {
    let mode = render('35812');
    expect(mode).toBe('-rwsr--r-T');

    mode = render('35813');
    expect(mode).toBe('-rwsr--r-t');
  });
});
