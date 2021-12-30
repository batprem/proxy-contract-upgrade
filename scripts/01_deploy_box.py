from scripts.helpful_script import get_account, encode_function_data, upgrade
from brownie import (
    network,
    Box,
    ProxyAdmin,
    TransparentUpgradeableProxy,
    Contract,
    BoxV2,
)
import time


ACTIVE_NETWORK = network.show_active()


def main():
    account = get_account()
    print(f"Deploying to {ACTIVE_NETWORK}")
    box = Box.deploy({"from": account}, publish_source=True)
    print(box.retrieve())

    # box.increment # Raise attibute error
    proxy_admin = ProxyAdmin.deploy({"from": account}, publish_source=True)
    box_encoded_initializer_function = encode_function_data()
    proxy = TransparentUpgradeableProxy.deploy(
        box.address,
        proxy_admin.address,
        box_encoded_initializer_function,
        {"from": account},
        publish_source=True,
    )
    print(f"Proxy deployed to {proxy}, you can now upgrade to v2!")
    box.store(1)
    proxy_box = Contract.from_abi("Box", proxy.address, Box.abi)
    proxy_box.store(1, {"from": account})
    print(proxy_box.retrieve())

    box_v2 = BoxV2.deploy({"from": account}, publish_source=True)
    upgrade_transaction = upgrade(
        account, proxy, box_v2.address, proxy_admin_contract=proxy_admin
    )
    upgrade_transaction.wait(1)
    print("Proxy has been upgraded!")
    proxy_box = Contract.from_abi("BoxV2", proxy.address, BoxV2.abi)
    print(proxy_box.retrieve())
    tx = proxy_box.increment({"from": account})
    print(proxy_box.retrieve())
