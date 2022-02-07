import {translateGrrUser} from '../../lib/api_translation/user';
import {initTestEnvironment} from '../../testing';

initTestEnvironment();

describe('User API translation', () => {
  it('converts ApiGrrUser to GrrUser correctly', () => {
    expect(translateGrrUser({username: 'test'})).toEqual({
      name: 'test',
      canaryMode: false,
      huntApprovalRequired: false,
    });
  });

  it('converts canaryMode correctly', () => {
    expect(translateGrrUser({
      username: 'test',
      settings: {canaryMode: true},
      interfaceTraits: {huntApprovalRequired: true},
    })).toEqual({
      name: 'test',
      canaryMode: true,
      huntApprovalRequired: true,
    });
  });
});
