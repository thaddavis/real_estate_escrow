from algosdk import account
from algosdk.future import transaction
from algosdk.v2client import algod
from algosdk.future import transaction
from algosdk import constants
import json
import base64
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).absolute().parent.parent))

from utility.general import get_private_key_from_mnemonic
# from utility.state import read_global_state
import config

if __name__ == "__main__":
    algod_client = algod.AlgodClient(config.algod_token, config.algod_address)
    # creator_private_key = get_private_key_from_mnemonic(config.creator_mnemonic)

    buyer_private_key = get_private_key_from_mnemonic(config.buyer_mnemonic)

    params = algod_client.suggested_params()
    params.flat_fee = True
    params.fee = constants.MIN_TXN_FEE 

    receiver = "X6VC6C2ZKFUNRN3AHUXGSS4QJO72YA667BI7GX6FMRSFHR26B3DUPDC5KE"
    sender = "RHKHUONCBB7JOIQ2RDCSV3NUX5JFKLLOG2RKN4LRIJ6DQMAIBTFLLO72DM"
    note = "Fund Escrow".encode()
    amount = 1222333
    
    unsigned_txn_A = transaction.PaymentTxn(
        sender,
        params,
        receiver,
        amount,
        None,
        note
    )

    app_args = [
        "deposit_escrow"
    ]
    unsigned_txn_B = transaction.ApplicationNoOpTxn(sender, params, config.app_id, app_args)

    gid = transaction.calculate_group_id([unsigned_txn_A, unsigned_txn_B])
    unsigned_txn_A.group = gid
    unsigned_txn_B.group = gid

    signed_txn_A = unsigned_txn_A.sign(buyer_private_key)
    signed_txn_B = unsigned_txn_B.sign(buyer_private_key)

    signed_group = [signed_txn_A, signed_txn_B]
    
    # submit transaction
    tx_id = algod_client.send_transactions(signed_group)

    # wait for confirmation 
    try:
        confirmed_txn = transaction.wait_for_confirmation(algod_client, tx_id, 4)  
    except Exception as err:
        print(err)

    print("Transaction information: {}".format(
        json.dumps(confirmed_txn, indent=4)))
    # print("Decoded note: {}".format(base64.b64decode(
    #     confirmed_txn["txn"]["txn"]["note"]).decode()))

    # account_info = algod_client.account_info(receiver)
    # print("Final Account balance: {} microAlgos".format(account_info.get('amount')) + "\n")