import {RESULT_KEY_SEPARATOR, ResultKey, toResultKey, toResultKeyString} from './result';

describe('Result', () => {
  describe('Result Key', () => {
    describe('toResultKeyString', () => {
      it('Converts a key correctly', () => {
        const testResultKey: ResultKey = {
          clientId: 'C.1234',
          flowId: 'ABCD1234',
          timestamp: '1',
        };

        const resultKeyId = toResultKeyString(testResultKey);

        expect(resultKeyId)
            .toEqual(`${testResultKey.clientId}${RESULT_KEY_SEPARATOR}${
                testResultKey.flowId}${RESULT_KEY_SEPARATOR}${
                testResultKey.timestamp}`);
      });
    });

    describe('toResultKey', () => {
      it('Converts a result key Id correctly', () => {
        const resultKeyId = 'C.1234-ABCD1234-1';

        const resultKey = toResultKey(resultKeyId);

        expect(resultKey.clientId).toEqual('C.1234');
        expect(resultKey.flowId).toEqual('ABCD1234');
        expect(resultKey.timestamp).toEqual('1');
      });

      it('Throws an exception is the result key Id is invalid (too short)',
         () => {
           const resultKeyId = '';

           expect(() => toResultKey(resultKeyId))
               .toThrow(new Error(`Error parsing result key "${
                   resultKeyId}": got length 1; expected 3`));
         });

      it('Throws an exception is the result key Id is invalid (too long)',
         () => {
           const resultKeyId = 'C.1234-ABCD1234-1-Peekaboo';

           expect(() => toResultKey(resultKeyId))
               .toThrow(new Error(`Error parsing result key "${
                   resultKeyId}": got length 4; expected 3`));
         });
    });
  });
});
