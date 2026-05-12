import {initTestEnvironment} from '../../testing';

import {isHuntApproval} from './hunt';
import {newClientApproval, newHuntApproval} from './model_test_util';

initTestEnvironment();

describe('Hunt model', () => {
  describe('isHuntApproval', () => {
    it('returns true for hunt approval', () => {
      expect(isHuntApproval(newHuntApproval({}))).toBeTrue();
    });
    it('returns false for client approval', () => {
      expect(isHuntApproval(newClientApproval({}))).toBeFalse();
    });
  });
});
