import {TestBed} from '@angular/core/testing';

import {ErrorSnackBar} from './error_snackbar/error_snackbar';
import {SnackBarErrorHandler} from './snackbar_error_handler';

describe('Snackbar Error Handler', () => {
  let snackBarErrorHandler: SnackBarErrorHandler;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [],
      providers: [SnackBarErrorHandler],
    }).compileComponents();

    snackBarErrorHandler = TestBed.inject(SnackBarErrorHandler);
  });

  it('calls snackbar with error message', () => {
    const snackbarSpy = spyOn(
      snackBarErrorHandler.snackBar,
      'openFromComponent',
    );
    snackBarErrorHandler.handleError(new Error('error message'));
    expect(snackbarSpy).toHaveBeenCalledWith(ErrorSnackBar, {
      data: 'error message',
    });
  });
});
