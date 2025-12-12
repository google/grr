import {CloudInstanceInstanceType} from '../api/api_interfaces';
import {
  archAccessor,
  cloudInstanceAccessor,
  hardwareInfoAccessor,
  isClientApproval,
  knowledgeBaseAccessor,
  memorySizeAccessor,
  networkInterfacesAccessor,
  osInstallDateAccessor,
  osKernelAccessor,
  osReleaseAccessor,
  osVersionAccessor,
  startupInfoAccessor,
  usersAccessor,
  volumesAccessor,
} from './client';
import {
  newClientApproval,
  newClientSnapshot,
  newHuntApproval,
} from './model_test_util';

describe('Client accessor function', () => {
  it('archAccessor returns correct value', () => {
    const client = newClientSnapshot({arch: 'test-machine'});
    expect(archAccessor(client)).toEqual('test-machine');
  });

  it('cloudInstanceAccessor returns correct value for Google cloud', () => {
    const client = newClientSnapshot({
      cloudInstance: {
        cloudType: CloudInstanceInstanceType.GOOGLE,
        google: {
          uniqueId: '1234567890',
          zone: 'google-zone',
          projectId: 'google-proj',
          instanceId: 'google-1234567890',
          hostname: 'google.host',
          machineType: 'google-type',
        },
        amazon: {},
      },
    });
    expect(cloudInstanceAccessor(client)).toEqual(
      'Unique ID: 1234567890\n' +
        'Zone: google-zone\n' +
        'Project ID: google-proj\n' +
        'Instance ID: google-1234567890\n' +
        'Hostname: google.host\n' +
        'Machine Type: google-type',
    );
  });

  it('cloudInstanceAccessor returns correct value for Amazon cloud', () => {
    const client = newClientSnapshot({
      cloudInstance: {
        cloudType: CloudInstanceInstanceType.AMAZON,
        google: {},
        amazon: {
          instanceId: '1234567890',
          hostname: 'amazon',
          publicHostname: 'amazon.host',
          amiId: 'amid-1234567890',
          instanceType: 'amazon-type',
        },
      },
    });
    expect(cloudInstanceAccessor(client)).toEqual(
      'Instance ID: 1234567890\n' +
        'Hostname: amazon\n' +
        'Public hostname: amazon.host\n' +
        'AMI ID: amid-1234567890\n' +
        'Instance type: amazon-type',
    );
  });

  it('cloudInstanceAccessor returns correct value for unknown cloud', () => {
    const client = newClientSnapshot({
      cloudInstance: {
        cloudType: CloudInstanceInstanceType.UNSET,
        google: {},
        amazon: {},
      },
    });
    expect(cloudInstanceAccessor(client)).toEqual('');
  });

  it('hardwareInfoAccessor returns correct value', () => {
    const client = newClientSnapshot({
      hardwareInfo: {
        systemManufacturer: 'test-manufacturer',
        systemFamily: 'test-system-family',
        systemProductName: 'test-system-product-name',
        serialNumber: 'test-serial-number',
        systemUuid: 'test-system-uuid',
        systemSkuNumber: 'test-system-sku-number',
        systemAssettag: 'test-system-assettag',
        biosVendor: 'test-bios-vendor',
        biosVersion: 'test-bios-version',
        biosReleaseDate: 'test-bios-release-date',
        biosRomSize: 'test-bios-rom-size',
        biosRevision: 'test-bios-revision',
      },
    });
    expect(hardwareInfoAccessor(client)).toEqual(
      'System Manufacturer: test-manufacturer\n' +
        'System Family: test-system-family\n' +
        'System Product Name: test-system-product-name\n' +
        'Serial Number: test-serial-number\n' +
        'System UUID: test-system-uuid\n' +
        'System SKU Number: test-system-sku-number\n' +
        'System Assettag: test-system-assettag\n' +
        'BIOS Vendor: test-bios-vendor\n' +
        'BIOS Version: test-bios-version\n' +
        'BIOS Release Date: test-bios-release-date\n' +
        'BIOS ROM Size: test-bios-rom-size\n' +
        'BIOS Revision: test-bios-revision',
    );
  });

  it('knowledgeBaseAccessor returns correct value', () => {
    const client = newClientSnapshot({
      knowledgeBase: {
        osMajorVersion: 10000,
        osMinorVersion: 20000,
        os: 'Foooo',
        fqdn: 'Foo.bar.com',
      },
    });
    expect(knowledgeBaseAccessor(client)).toEqual(
      'OS: Foooo\n' +
        'FQDN: Foo.bar.com\n' +
        'OS Major Version: 10000\n' +
        'OS Minor Version: 20000',
    );
  });

  it('memorySizeAccessor returns correct value', () => {
    const client = newClientSnapshot({
      memorySize: BigInt(1024 * 1024 * 1024),
    });
    expect(memorySizeAccessor(client)).toEqual('1073741824 bytes');
  });

  it('networkInterfacesAccessor returns correct value', () => {
    const client = newClientSnapshot({
      networkInterfaces: [
        {
          macAddress: 'my:mac:address',
          interfaceName: 'test-network-interface',
          addresses: [
            {
              addressType: 'custom-address-type',
              ipAddress: '1.2.3.4',
            },
            {
              addressType: 'another-address-type',
              ipAddress: '9.8.7.6',
            },
          ],
        },
        {interfaceName: 'test-network-interface-2', addresses: []},
      ],
    });
    expect(networkInterfacesAccessor(client)).toEqual(
      'test-network-interface,\ntest-network-interface-2',
    );
  });

  it('osInstallDateAccessor returns correct value', () => {
    const client = newClientSnapshot({
      installTime: new Date('2024-01-01T00:00:00Z'),
    });
    expect(osInstallDateAccessor(client)).toEqual(
      'Mon, 01 Jan 2024 00:00:00 GMT',
    );
  });

  it('osKernelAccessor returns correct value', () => {
    const client = newClientSnapshot({
      kernel: 'Nut',
    });
    expect(osKernelAccessor(client)).toEqual('Nut');
  });

  it('osReleaseAccessor returns correct value', () => {
    const client = newClientSnapshot({
      osRelease: 'osRelease',
    });
    expect(osReleaseAccessor(client)).toEqual('osRelease');
  });

  it('osVersionAccessor returns correct value', () => {
    const client = newClientSnapshot({
      osVersion: 'osVersion',
    });
    expect(osVersionAccessor(client)).toEqual('osVersion');
  });

  it('startupInfoAccessor returns correct value', () => {
    const client = newClientSnapshot({
      startupInfo: {
        bootTime: new Date('2024-01-01T00:00:00Z'),
        clientInfo: {
          clientName: 'test-client-name',
          clientVersion: 123,
          buildTime: new Date('2024-01-01T00:00:00Z'),
          clientBinaryName: 'test-client-binary-name',
          clientDescription: 'test-client-description',
          sandboxSupport: true,
          timelineBtimeSupport: true,
        },
      },
    });
    expect(startupInfoAccessor(client)).toEqual(
      'Boot Time: Mon, 01 Jan 2024 00:00:00 GMT\n' +
        'Client Name: test-client-name\n' +
        'Client Version: 123\n' +
        'Build Time: Mon, 01 Jan 2024 00:00:00 GMT\n' +
        'Binary Name: test-client-binary-name\n' +
        'Description: test-client-description\n' +
        'Sandboxing supported: true\n' +
        'Btime supported: true',
    );
  });

  it('usersAccessor returns correct value', () => {
    const client = newClientSnapshot({
      users: [
        {
          username: 'testuser',
          fullName: 'Test User',
          lastLogon: new Date('435023333000'),
          homedir: '/home/testuser',
          uid: 54321,
          gid: 12345,
          shell: '/bin/bash',
        },
        {
          username: 'testuser2',
          fullName: 'Test User 2',
          lastLogon: new Date('435024444000'),
          homedir: '/home/testuser2',
          uid: 654321,
          gid: 23456,
          shell: '/bin/bash2',
        },
      ],
    });
    expect(usersAccessor(client)).toEqual('testuser,\ntestuser2');
  });

  it('volumesAccessor returns correct value', () => {
    const client = newClientSnapshot({
      volumes: [
        {
          name: 'Foo',
          devicePath: '/foo/bar',
          fileSystemType: 'test-file-system-type',
          totalSize: BigInt(5 * 1024 * 1024 * 1024),
          bytesPerSector: BigInt(512),
          freeSpace: BigInt(1024 * 1024 * 1024),
          creationTime: new Date('2020-07-01T13:00:00.000Z'),
          unixDetails: {
            mountPoint: '/mount/baz/',
            mountOptions: 'test-mount-options',
          },
          windowsDetails: {
            attributes: ['test-attribute1', 'test-attribute2'],
            driveLetter: 'Z',
            driveType: 'test-drive-type',
          },
        },
        {
          devicePath: '/foo/baz',
        },
      ],
    });
    expect(volumesAccessor(client)).toEqual(
      'Device path: /foo/bar\n' +
        'File system type: test-file-system-type\n' +
        'Free space: 1073741824 bytes,\n\n' +
        'Device path: /foo/baz\n' +
        'File system type: ?\n' +
        'Free space: ? bytes',
    );
  });

  describe('isClientApproval', () => {
    it('returns true for client approval', () => {
      expect(isClientApproval(newClientApproval({}))).toBeTrue();
    });
    it('returns false for hunt approval', () => {
      expect(isClientApproval(newHuntApproval({}))).toBeFalse();
    });
  });
});
