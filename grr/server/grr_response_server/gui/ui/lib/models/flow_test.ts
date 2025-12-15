import {isFlowResult} from './flow';
import {newFlowResult, newHuntResult} from './model_test_util';

describe('Flow model', () => {
  it('isFlowResult', () => {
    expect(isFlowResult(newFlowResult({tag: 'foo'}))).toBeTrue();
    expect(isFlowResult(newHuntResult({}))).toBeFalse();
  });
});
