#include "grr/client/minicomm/client_actions/enumerate_interfaces.h"

#include <sys/socket.h>
#include <netpacket/packet.h>
#include <netinet/in.h>

#include <cstring>

#include "gtest/gtest.h"
#include "grr/client/minicomm/base.h"
#include "grr/client/minicomm/util.h"

namespace grr {
namespace actions {

TEST(EnumerateInterfacesTest, ProcessIfaddrList) {
  char kEth0[] = "eth0";
  const char kMacAddr[] = "\xFF\x00\xFE\x01\xFD\x02";
  const char kIp6Addr[] =
      "\xFF\x00\xFE\x01\xFD\x02\xFC\x03\xFB\x04\xFA\x05\xF9\x06\xF8\x07";
  constexpr uint32 kIp4Addr = 0xC0A80102ul;  // 192.168.1.2
  const char kIp4AddrBytes[] = "\xC0\xA8\x01\x02";

  struct sockaddr_ll eth0_mac_addr = {};
  eth0_mac_addr.sll_family = AF_PACKET;
  eth0_mac_addr.sll_halen = 6;
  std::memcpy(&eth0_mac_addr.sll_addr, kMacAddr, 6);

  struct ifaddrs eth0_mac = {};
  eth0_mac.ifa_name = kEth0;
  eth0_mac.ifa_addr = reinterpret_cast<struct sockaddr*>(&eth0_mac_addr);

  struct sockaddr_in eth0_ip_addr = {};
  eth0_ip_addr.sin_family = AF_INET;
  eth0_ip_addr.sin_addr.s_addr = htonl(kIp4Addr);

  struct ifaddrs eth0_ip = {};
  eth0_ip.ifa_name = kEth0;
  eth0_ip.ifa_addr = reinterpret_cast<struct sockaddr*>(&eth0_ip_addr);
  eth0_ip.ifa_next = &eth0_mac;

  struct sockaddr_in6 eth0_ip6_addr = {};
  eth0_ip6_addr.sin6_family = AF_INET6;
  std::memcpy(&eth0_ip6_addr.sin6_addr.s6_addr, kIp6Addr, 16);

  struct ifaddrs eth0_null = {};
  eth0_null.ifa_name = kEth0;
  eth0_null.ifa_addr = nullptr;
  eth0_null.ifa_next = &eth0_ip;

  struct ifaddrs eth0_ip6 = {};
  eth0_ip6.ifa_name = kEth0;
  eth0_ip6.ifa_addr = reinterpret_cast<struct sockaddr*>(&eth0_ip6_addr);
  eth0_ip6.ifa_next = &eth0_null;

  EnumerateInterfaces action;
  auto result = action.ProcessIfaddrList(&eth0_ip6);
  EXPECT_EQ(1, result.size());
  EXPECT_EQ(std::string(kMacAddr, 6), result[kEth0].mac_address());
  EXPECT_EQ(2, result[kEth0].addresses_size());
  for (const auto& addr : result[kEth0].addresses()) {
    if (addr.address_type() == NetworkAddress::INET) {
      EXPECT_EQ(std::string(kIp4AddrBytes, 4), addr.packed_bytes());
    }
    if (addr.address_type() == NetworkAddress::INET6) {
      EXPECT_EQ(std::string(kIp6Addr, 16), addr.packed_bytes());
    }
  }
}
}  // namespace actions
}  // namespace grr
