import brownie
from brownie import (
    accounts,
    config,
    network,
    MockV3Aggregator,
    Contract,
    VRFCoordinatorMock,
    LinkToken,
    interface,
)
from brownie.project.main import new
from web3 import Web3
import eth_utils


OPENSEA_URL = "https://testnets.opensea.io/assets/{}/{}"
FORKED_LOCAL_ENVIRONMENTS = ["mainnet-fork", "mainnet-fork-dev"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache-local", "ganache-local-2"]


DECIMALS = 8
STARTING_PRICE = 2e8
BREED_MAPPING = ["PUG", "SHIBA_INU", "ST_BERNARD"]


def get_account(index=None, account_id=None):
    active_network = network.show_active()
    if index:
        return accounts[index]
    if account_id:
        return accounts.load(account_id)
    if (
        active_network in LOCAL_BLOCKCHAIN_ENVIRONMENTS
        or active_network in FORKED_LOCAL_ENVIRONMENTS
    ):
        return accounts[0]
    else:
        return accounts.add(config["wallet"]["from_key"])


contract_to_mock = {
    "eth_usd_price_feed": MockV3Aggregator,
    "vrf_coordinator": VRFCoordinatorMock,
    "link_token": LinkToken,
}


def get_contract(contract_name):
    """
    This function will grab the contract address from the brownie config

    Args:
        contract_name (string)
    Returns:
        brownie.network.contract.ProjectContract
    """
    active_network = network.show_active()
    contract_type = contract_to_mock[contract_name]
    if active_network in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        # Note that Local networks do not contain chain link contract address by default
        # we need to monk them up
        if len(contract_type) <= 0:
            # Get the latest deployed contract, deploy one if doesn't exist
            deploy_mocks()
        contract = contract_type[-1]
    else:
        contract_address = config["networks"][active_network][contract_name]
        # address
        # ABI
        contract = Contract.from_abi(
            contract_type._name, contract_address, contract_type.abi
        )
    return contract


def deploy_mocks():
    """
    Deploy mock contract
    """
    account = get_account()
    print(f"The active network is {network.show_active()}")
    print("Deploying Mock...")

    MockV3Aggregator.deploy(
        DECIMALS, Web3.toWei(STARTING_PRICE, "ether"), {"from": account}
    )
    link_token = LinkToken.deploy({"from": account})

    VRFCoordinatorMock.deploy(link_token.address, {"from": account})
    print("Mocks deployed")


def fund_contract_with_link(
    contract_address: str,
    account: brownie.network.account.Account = None,
    link_token: Contract = None,
    amount: int = 0.1e18,
):
    """
    Contract which call external API need link token for request
    As a result, we first need to fund contract with link token
    """
    account = account if account else get_account()
    link_token = link_token if link_token else get_contract("link_token")
    # tx = link_token.transfer(contract_address, amount, {"from", amount})
    link_token_contract = interface.LinkTokenInterface(link_token.address)
    link_token_contract.transfer(contract_address, amount, {"from": account})
    print("Fund contract")


def get_breed(breed_number):
    return BREED_MAPPING[breed_number]


# initializer = box.store, 1, 2
def encode_function_data(initializer=None, *args):
    """Encodes the function call so we can work with an initializer.
    Args:
        initializer ([brownie.network.contract.ContractTx], optional):
        The initializer function we want to call. Example: `box.store`.
        Defaults to None.
        args (Any, optional):
        The arguments to pass to the initializer function
    Returns:
        [bytes]: Return the encoded bytes.
    """
    if len(args) == 0 or not initializer:
        return eth_utils.to_bytes(hexstr="0x")
    return initializer.encode_input(*args)


def upgrade(
    account,
    proxy,
    newimplementation_address,
    proxy_admin_contract=None,
    initializer=None,
    *args,
):
    transaction = None
    if proxy_admin_contract:
        if initializer:
            encoded_function_call = encode_function_data(initializer, *args)
            transaction = proxy_admin_contract.upgradeAndCall(
                proxy.address,
                newimplementation_address,
                encoded_function_call,
                {"from": account},
            )
        else:
            transaction = proxy_admin_contract.upgrade(
                proxy.address, newimplementation_address, {"from": account}
            )
    else:
        if initializer:
            encoded_function_call = encode_function_data(initializer, *args)
            transaction = proxy.upgradeToAndCall(
                newimplementation_address, encoded_function_call, {"from": account}
            )
        else:
            transaction = proxy.upgradeTo(newimplementation_address, {"from": account})
    return transaction
