import {TestBed} from '@angular/core/testing';

import {SanitizerPipe} from './sanitizer_pipe';

describe('Sanitizer Pipe', () => {
  let pipe: SanitizerPipe;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [SanitizerPipe],
    });
    pipe = TestBed.inject(SanitizerPipe);
  });

  it('returns null if the html snippet is undefined', () => {
    expect(pipe.transform(undefined)).toBe(null);
  });

  it('returns the same content if the html snippet is safe', () => {
    expect(pipe.transform('<div>Hello</div>')).toBe('<div>Hello</div>');
  });

  it('strips out the unsafe content if it is unsafe', () => {
    expect(
      pipe.transform(
        '<div><script type="text/javascript">window.alert("fo")</script></div>',
      ),
    ).toBe('<div></div>');
  });
});
