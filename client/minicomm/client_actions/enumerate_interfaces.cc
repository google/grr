#include "grr/client/minicomm/client_actions/enumerate_interfaces.h"

#include <ifaddrs.h>
#include <netpacket/packet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>

#include <memory>

#include "grr/client/minicomm/util.h"

namespace grr {
namespace actions {

template <class T>
std::string ToBytes(const T& input) {
  return std::string(static_cast<const char*>(static_cast<const void*>(&input)),
                     sizeof(input));
}

void EnumerateInterfaces::ProcessRequest(ActionContext* context) {
  struct ifaddrs* addresses = nullptr;
  if (getifaddrs(&addresses)) {
    context->SetError("Getifaddr failed with error: " + ErrorName(errno));
    if (addresses != nullptr) {
      freeifaddrs(addresses);
    }
    return;
  }
  InterfaceMap interfaces = ProcessIfaddrList(addresses);

  freeifaddrs(addresses);
  for (const auto& p : interfaces) {
    context->SendResponse(p.second, GrrMessage::MESSAGE);
  }
}

EnumerateInterfaces::InterfaceMap EnumerateInterfaces::ProcessIfaddrList(
    const struct ifaddrs* addresses) {
  InterfaceMap interfaces;

  for (auto p = addresses; p != nullptr; p = p->ifa_next) {
    const std::string name(p->ifa_name);
    Interface& result = interfaces[name];
    if (result.ifname() == "") {
      result.set_ifname(name);
    }

    // This will occur typically on Android's usb interfaces, but it's possible
    // to occur on *nix as well
    if (p->ifa_addr == nullptr) {
      continue;
    }

    switch (p->ifa_addr->sa_family) {
      case AF_INET: {
        const auto ip_addr = reinterpret_cast<struct sockaddr_in*>(p->ifa_addr);
        NetworkAddress* net_address = result.add_addresses();
        net_address->set_address_type(NetworkAddress::INET);
        // It seems that s_addr is already in network byte order.
        net_address->set_packed_bytes(ToBytes(ip_addr->sin_addr.s_addr));
      } break;
      case AF_INET6: {
        const auto ip6_addr =
            reinterpret_cast<struct sockaddr_in6*>(p->ifa_addr);
        NetworkAddress* net_address = result.add_addresses();
        net_address->set_address_type(NetworkAddress::INET6);
        net_address->set_packed_bytes(ToBytes(ip6_addr->sin6_addr.s6_addr));
      } break;
      case AF_PACKET: {
        const auto sock_addr =
            reinterpret_cast<struct sockaddr_ll*>(p->ifa_addr);
        result.set_mac_address(
            std::string(reinterpret_cast<char*>(sock_addr->sll_addr),
                        std::min(size_t(sock_addr->sll_halen),
                                 sizeof(sock_addr->sll_addr))));
      } break;
    }
  }
  return interfaces;
}
}  // namespace actions
}  // namespace grr
