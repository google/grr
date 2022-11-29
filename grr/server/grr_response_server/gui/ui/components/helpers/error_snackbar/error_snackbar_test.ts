import {Clipboard} from '@angular/cdk/clipboard';
import {OverlayContainer} from '@angular/cdk/overlay';
import {HarnessLoader} from '@angular/cdk/testing';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component, ViewContainerRef} from '@angular/core';
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {MatSnackBar, MatSnackBarModule} from '@angular/material/snack-bar';
import {MatSnackBarHarness} from '@angular/material/snack-bar/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {DeepPartial} from '../../../lib/type_utils';

import {ErrorSnackBar, WINDOW} from './error_snackbar';
import {ErrorSnackBarModule} from './error_snackbar_module';

@Component({})
class TestHostComponent {
  constructor(public viewContainerRef: ViewContainerRef) {}
}

describe('ErrorSnackBar Component', () => {
  let loader: HarnessLoader;
  let fixture: ComponentFixture<TestHostComponent>;
  let clipboard: Partial<Clipboard>;
  let window: DeepPartial<Window>;

  beforeEach((() => {
    clipboard = {
      copy: jasmine.createSpy('copy').and.returnValue(true),
    };
    window = {
      location: {
        reload: jasmine.createSpy('reload'),
      }
    };

    TestBed
        .configureTestingModule({
          imports: [
            MatSnackBarModule, ErrorSnackBarModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
          ],
          declarations: [TestHostComponent],
          providers: [
            {
              provide: OverlayContainer,
              useFactory: () =>
                  ({getContainerElement: () => fixture.nativeElement}),
            },
            {
              provide: Clipboard,
              useFactory: () => clipboard,
            },
            {
              provide: WINDOW,
              useFactory: () => window,
            },
          ]
        })
        .compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  }));

  it('should contain the error message', async () => {
    const snackBar = TestBed.inject(MatSnackBar);
    expect((await loader.getAllHarnesses(MatSnackBarHarness)).length).toBe(0);

    snackBar.openFromComponent(ErrorSnackBar, {data: 'testerror'});

    expect((await loader.getAllHarnesses(MatSnackBarHarness)).length).toBe(1);

    expect(fixture.nativeElement.textContent).toContain('testerror');
  });

  it('reloads the window when clicking on reload', async () => {
    const snackBar = TestBed.inject(MatSnackBar);
    snackBar.openFromComponent(ErrorSnackBar, {data: 'testerror'});

    expect((await loader.getAllHarnesses(MatSnackBarHarness)).length).toBe(1);

    expect(window.location?.reload).not.toHaveBeenCalled();

    fixture.nativeElement.querySelector('button[aria-label="reload"]').click();

    expect(window.location?.reload).toHaveBeenCalledOnceWith();
  });

  it('shows a copy confirmation when clicking on copy', async () => {
    const snackBar = TestBed.inject(MatSnackBar);
    snackBar.openFromComponent(ErrorSnackBar, {data: 'testerror'});

    expect((await loader.getAllHarnesses(MatSnackBarHarness)).length).toBe(1);
    fixture.detectChanges();

    fixture.nativeElement.querySelector('button[aria-label="copy"]').click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('button[aria-label="copy"]'))
        .toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Copied');
    expect(fixture.nativeElement.textContent).not.toContain('testerror');
    expect((await loader.getAllHarnesses(MatSnackBarHarness)).length).toBe(1);
  });

  it('copies the error message to the clipboard when clicking on copy',
     async () => {
       const snackBar = TestBed.inject(MatSnackBar);
       snackBar.openFromComponent(ErrorSnackBar, {data: 'testerror'});

       expect(clipboard.copy).not.toHaveBeenCalled();

       fixture.nativeElement.querySelector('button[aria-label="copy"]').click();

       expect(clipboard.copy).toHaveBeenCalledOnceWith('testerror');
     });
});
