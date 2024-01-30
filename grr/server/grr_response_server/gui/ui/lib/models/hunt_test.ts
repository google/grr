import {initTestEnvironment} from '../../testing';

import {getHuntTitle} from './hunt';
import {newHunt} from './model_test_util';

initTestEnvironment();

describe('getHuntTitle', () => {
  it('undefined hunt', () => {
    expect(getHuntTitle(null)).toEqual('Untitled fleet collection');
  });

  it('description only', () => {
    expect(
      getHuntTitle(
        newHunt({
          description: 'description',
          name: undefined,
          flowName: undefined,
        }),
      ),
    ).toEqual('description');
  });

  it('generic name only', () => {
    expect(
      getHuntTitle(
        newHunt({
          description: undefined,
          name: 'GenericHunt',
          flowName: undefined,
        }),
      ),
    ).toEqual('Untitled fleet collection');
  });

  it('generic name with flow information', () => {
    expect(
      getHuntTitle(
        newHunt({
          description: undefined,
          name: 'GenericHunt',
          flowName: 'SomeFlow',
        }),
      ),
    ).toEqual('Untitled fleet collection: SomeFlow');
  });

  it('empty name with flow information', () => {
    expect(
      getHuntTitle(
        newHunt({
          description: undefined,
          name: '', // should be treated the same as undefined/GenericHunt
          flowName: 'SomeFlow',
        }),
      ),
    ).toEqual('Untitled fleet collection: SomeFlow');
  });

  it('proper name', () => {
    expect(
      getHuntTitle(
        newHunt({
          description: '', // should be treated the same as undefined
          name: 'name',
          flowName: 'SomeFlow',
        }),
      ),
    ).toEqual('name');
  });

  it('all fields set', () => {
    expect(
      getHuntTitle(
        newHunt({
          description: 'description',
          name: 'GenericHunt',
          flowName: 'SomeFlow',
        }),
      ),
    ).toEqual('description');
  });
});
