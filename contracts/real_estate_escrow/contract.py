import sys
from pathlib import Path
sys.path.append(str(Path(__file__).absolute().parent.parent.parent))
from pyteal import *
from pyteal_helpers import program

UINT64_MAX=0xffffffffffffffff

def approval_program():
    
    global_creator=Bytes("creator") # byteslice
    global_seller=Bytes("seller") # byteslice
    global_buyer=Bytes("buyer") # byteslice
    global_app_id=Bytes("app_id") # byteslice
    
    pull_out=Bytes("pull_out") # CONSTANT
    buyer_withdraw_funds=Bytes("buyer_withdraw_funds") # CONSTANT
    seller_withdraw_funds=Bytes("seller_withdraw_funds") # CONSTANT
    global_trigger_pull_out_called_counter = Bytes("trigger_pull_out_called_counter") # CONSTANT

    scratch_int = ScratchVar(TealType.uint64)
    
    trigger_pull_out=Seq(
        scratch_int.store(App.globalGet(global_trigger_pull_out_called_counter)),
        # detect overflow
        If(
            scratch_int.load() < Int(UINT64_MAX)
        )
        .Then(
            App.globalPut(global_trigger_pull_out_called_counter, App.globalGet(global_trigger_pull_out_called_counter) + Int(1))    
        ),
        Approve()
    )

    trigger_seller_withdraw_funds=Seq(
        If(
            And(
                Txn.first_valid() >= App.globalGet(Bytes("inspection_end")),
                App.globalGet(global_trigger_pull_out_called_counter) == Int(0),
                Txn.type_enum() == TxnType.Payment,
                Txn.close_remainder_to() == Global.zero_address(),
                Txn.rekey_to() == Global.zero_address(),
                Or(
                    Txn.sender() == App.globalGet(Bytes("seller")),
                    Txn.receiver() == App.globalGet(Bytes("seller")),
                )
            )
        ).Then(
            Approve()
        ).Else(
            Reject()
        )
    )

    trigger_buyer_withdraw_funds=Seq(
        Approve()
    )

    return program.event(
        init=Seq(
            App.globalPut(global_creator, Txn.sender()),
            App.globalPut(global_app_id, Txn.application_id()),
            App.globalPut(Bytes("inspection_begin"), Btoi(Txn.application_args[0])),
            App.globalPut(Bytes("inspection_end"), Btoi(Txn.application_args[1])),
            App.globalPut(Bytes("sale_price"), Btoi(Txn.application_args[2])),
            App.globalPut(Bytes("escrow_amount"), Btoi(Txn.application_args[3])),
            App.globalPut(global_buyer, Txn.application_args[4]),
            App.globalPut(global_seller, Txn.application_args[5]),
            App.globalPut(global_trigger_pull_out_called_counter, Int(0)),
            Approve()
        ),
        no_op=Cond(
            [
                Txn.application_args[0] == pull_out,
                trigger_pull_out
            ],
            [
                Txn.application_args[0] == seller_withdraw_funds,
                trigger_seller_withdraw_funds
            ],
            [
                Txn.application_args[0] == buyer_withdraw_funds,
                trigger_buyer_withdraw_funds
            ]
        )
    )

def clear_state_program():
    return Approve()