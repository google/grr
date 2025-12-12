import {initTestEnvironment} from '../../testing';

import {isHuntApproval, isHuntResult} from './hunt';
import {
  newClientApproval,
  newFlowResult,
  newHuntApproval,
  newHuntResult,
} from './model_test_util';

initTestEnvironment();

describe('Hunt model', () => {
  describe('isHuntResult', () => {
    it('returns true for hunt result', () => {
      expect(isHuntResult(newHuntResult({}))).toBeTrue();
    });

    it('returns false for flow result', () => {
      expect(isHuntResult(newFlowResult({}))).toBeFalse();
    });
  });

  describe('isHuntApproval', () => {
    it('returns true for hunt approval', () => {
      expect(isHuntApproval(newHuntApproval({}))).toBeTrue();
    });
    it('returns false for client approval', () => {
      expect(isHuntApproval(newClientApproval({}))).toBeFalse();
    });
  });
});
