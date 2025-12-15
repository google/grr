import {Clipboard} from '@angular/cdk/clipboard';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed} from '@angular/core/testing';
import {MAT_SNACK_BAR_DATA, MatSnackBarRef} from '@angular/material/snack-bar';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';
import {ErrorSnackBar, WINDOW} from './error_snackbar';
import {ErrorSnackBarHarness} from './testing/error_snackbar_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ErrorSnackBar);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ErrorSnackBarHarness,
  );
  return {fixture, harness};
}

const TEST_ERROR_MESSAGE = 'testerror';

describe('ErrorSnackBar Component', () => {
  let clipboard: Partial<Clipboard>;
  let windowMock: Window;
  let snackBarRef: jasmine.SpyObj<MatSnackBarRef<ErrorSnackBar>>;

  beforeEach(() => {
    clipboard = {
      copy: jasmine.createSpy('copy').and.returnValue(true),
    };
    windowMock = {
      location: {
        reload: jasmine.createSpy('reload'),
      },
    } as unknown as Window;
    snackBarRef = jasmine.createSpyObj('MatSnackBarRef', ['dismiss']);

    TestBed.configureTestingModule({
      imports: [ErrorSnackBar, NoopAnimationsModule],
      providers: [
        {
          provide: Clipboard,
          useFactory: () => clipboard,
        },
        {
          provide: MAT_SNACK_BAR_DATA,
          useValue: TEST_ERROR_MESSAGE,
        },
        {
          provide: MatSnackBarRef,
          useValue: snackBarRef,
        },
      ],
    })
      .overrideComponent(ErrorSnackBar, {
        set: {
          providers: [
            {
              provide: WINDOW,
              useValue: windowMock,
            },
          ],
        },
      })
      .compileComponents();
  });

  it('should contain the error message and copy button', async () => {
    const {harness} = await createComponent();

    expect(await (await harness.host()).text()).toContain(TEST_ERROR_MESSAGE);
    expect(await harness.copyButton()).not.toBeNull();
    expect(await harness.copyConfirmation()).toBeNull();
  });

  it('reloads the window when clicking on reload', async () => {
    const {harness} = await createComponent();

    const reloadButton = await harness.reloadButton();
    await reloadButton.click();

    expect(windowMock.location?.reload).toHaveBeenCalledOnceWith();
  });

  it('shows a copy confirmation when clicking on copy', async () => {
    const {harness} = await createComponent();

    const copyButton = await harness.copyButton();
    await copyButton.click();

    expect(await harness.copyConfirmation()).not.toBeNull();
    expect(await harness.copyIcon()).toBeNull();
  });

  it('copies the error message to the clipboard when clicking on copy', async () => {
    const {harness} = await createComponent();

    const copyButton = await harness.copyButton();
    await copyButton.click();

    expect(clipboard.copy).toHaveBeenCalledOnceWith(TEST_ERROR_MESSAGE);
  });
});
