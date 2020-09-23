import {initTestEnvironment} from '../../testing';

import {createDate, createIpv4Address, createIpv6Address, createMacAddress, createOptionalDate, createOptionalDateSeconds, decodeBase64, leastSignificantByteToHex} from './primitive';


initTestEnvironment();

describe('createDate', () => {
  it('throws for empty string', () => {
    expect(() => createDate('')).toThrowError(/Date/);
  });
  it('throws for invalid string', () => {
    expect(() => createDate('123abc')).toThrowError(/invalid/);
  });
  it('handles unix epoch correctly', () => {
    expect(createDate('0')).toEqual(new Date(0));
  });
  it('handles unixtimes correctly', () => {
    expect(createDate('1579167695123000')).toEqual(new Date(1579167695123));
  });
  it('truncates microseconds', () => {
    expect(createDate('1579167695123999')).toEqual(new Date(1579167695123));
  });
  it('handles future timestamps', () => {
    const y2100 = 130 * 365 * 86400 * 1000;
    expect(createDate((y2100 * 1000).toString())).toEqual(new Date(y2100));
  });
});

describe('createOptionalDate', () => {
  it('returns undefined for undefined', () => {
    expect(createOptionalDate(undefined)).toBeUndefined();
  });
  it('returns undefined for empty string', () => {
    expect(createOptionalDate('')).toBeUndefined();
  });
  it('throws for invalid string', () => {
    expect(() => createOptionalDate('123abc')).toThrowError(/invalid/);
  });
  it('handles unix epoch correctly', () => {
    expect(createOptionalDate('0')).toEqual(new Date(0));
  });
  it('handles unixtimes correctly', () => {
    expect(createOptionalDate('1579167695123000'))
        .toEqual(new Date(1579167695123));
  });
  it('truncates microseconds', () => {
    expect(createOptionalDate('1579167695123999'))
        .toEqual(new Date(1579167695123));
  });
  it('handles future timestamps', () => {
    const y2100 = 130 * 365 * 86400 * 1000;
    expect(createOptionalDate((y2100 * 1000).toString()))
        .toEqual(new Date(y2100));
  });
});

describe('createOptionalDateSeconds', () => {
  it('returns undefined for undefined', () => {
    expect(createOptionalDateSeconds(undefined)).toBeUndefined();
  });
  it('returns undefined for empty string', () => {
    expect(createOptionalDateSeconds('')).toBeUndefined();
  });
  it('throws for invalid string', () => {
    expect(() => createOptionalDateSeconds('123abc')).toThrowError(/invalid/);
  });
  it('handles unix epoch correctly', () => {
    expect(createOptionalDateSeconds('0')).toEqual(new Date(0));
  });
  it('handles unixtimes correctly', () => {
    expect(createOptionalDateSeconds('1579167695'))
        .toEqual(new Date(1579167695000));
  });
});

describe('decodeBase64', () => {
  it('returns empty byte array for undefined', () => {
    expect(decodeBase64(undefined)).toEqual(new Uint8Array(0));
  });

  it('throws an error on invalid input', () => {
    expect(() => decodeBase64('Inv@lid $tring')).toThrowError();
  });

  it('returns correct byte array for a base64 encoded string ', () => {
    expect(decodeBase64('yv66vg==')).toEqual(new Uint8Array([
      0xCA, 0xFE, 0xBA, 0xBE
    ]));
  });
});

describe('leastSignificantByteToHex', () => {
  it('translates only the least significant byte', () => {
    expect(leastSignificantByteToHex(0xBABE)).toEqual('BE');
  });

  it('adds 0 padding on front', () => {
    expect(leastSignificantByteToHex(0x1)).toEqual('01');
    expect(leastSignificantByteToHex(0xA)).toEqual('0A');
  });
});

describe('createIpv4Address', () => {
  it('creates an empty string on non 4 bytes array input', () => {
    expect(createIpv4Address(new Uint8Array(0))).toEqual('');
    expect(createIpv4Address(new Uint8Array([1, 2, 3]))).toEqual('');
    expect(createIpv4Address(new Uint8Array([1, 2, 3, 4, 5]))).toEqual('');
  });

  it('creates the IPv4 address representation of a 4 bytes array', () => {
    expect(createIpv4Address(new Uint8Array([1, 2, 3, 4]))).toEqual('1.2.3.4');
    expect(createIpv4Address(new Uint8Array([127, 0, 0, 1])))
        .toEqual('127.0.0.1');
    expect(createIpv4Address(new Uint8Array([255, 255, 255, 255])))
        .toEqual('255.255.255.255');
    expect(createIpv4Address(new Uint8Array([256, 256, 256, 256])))
        .toEqual('0.0.0.0');
    expect(createIpv4Address(new Uint8Array([0, 0, 0, 0]))).toEqual('0.0.0.0');
    expect(createIpv4Address(new Uint8Array([-1, -1, -1, -1])))
        .toEqual('255.255.255.255');
  });
});

describe('createIpv6Address', () => {
  it('creates an empty string on non 16 bytes array input', () => {
    expect(createIpv6Address(new Uint8Array(0))).toEqual('');
    expect(createIpv6Address(new Uint8Array([
      1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
    ]))).toEqual('');
    expect(createIpv6Address(new Uint8Array([
      1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17
    ]))).toEqual('');
  });

  it('creates the IPv6 non-abbreviated address representation of a 16 bytes array',
     () => {
       expect(createIpv6Address(new Uint8Array([
         1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
       ]))).toEqual('0102:0304:0506:0708:090A:0B0C:0D0E:0F10');
       expect(createIpv6Address(new Uint8Array([
         255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
         255, 255
       ]))).toEqual('FFFF:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF');
       expect(createIpv6Address(new Uint8Array([
         256, 256, 256, 256, 256, 256, 256, 256, 256, 256, 256, 256, 256, 256,
         256, 256
       ]))).toEqual('0000:0000:0000:0000:0000:0000:0000:0000');
       expect(createIpv6Address(new Uint8Array([
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
       ]))).toEqual('0000:0000:0000:0000:0000:0000:0000:0000');
       expect(createIpv6Address(new Uint8Array([
         -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1
       ]))).toEqual('FFFF:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF');
     });
});

describe('createMacAddress', () => {
  it('creates an empty string on non 6 bytes array input', () => {
    expect(createMacAddress(new Uint8Array(0))).toEqual('');
    expect(createMacAddress(new Uint8Array([1, 2, 3, 4, 5]))).toEqual('');
    expect(createMacAddress(new Uint8Array([1, 2, 3, 4, 5, 6, 7]))).toEqual('');
  });

  it('creates the MAC address representation of a 6 bytes array', () => {
    expect(createMacAddress(new Uint8Array([1, 2, 3, 4, 5, 6])))
        .toEqual('01:02:03:04:05:06');
    expect(createMacAddress(new Uint8Array([10, 11, 12, 13, 14, 15])))
        .toEqual('0A:0B:0C:0D:0E:0F');
    expect(createMacAddress(new Uint8Array([255, 255, 255, 255, 255, 255])))
        .toEqual('FF:FF:FF:FF:FF:FF');
    expect(createMacAddress(new Uint8Array([256, 256, 256, 256, 256, 256])))
        .toEqual('00:00:00:00:00:00');
    expect(createMacAddress(new Uint8Array([0, 0, 0, 0, 0, 0])))
        .toEqual('00:00:00:00:00:00');
    expect(createMacAddress(new Uint8Array([-1, -1, -1, -1, -1, -1])))
        .toEqual('FF:FF:FF:FF:FF:FF');
  });
});
