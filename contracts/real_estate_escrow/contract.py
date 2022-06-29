import sys
from pathlib import Path
sys.path.append(str(Path(__file__).absolute().parent.parent.parent))
from pyteal import *
from pyteal_helpers import program

UINT64_MAX=0xffffffffffffffff

def approval_program():
    # vvv vvv vvv
    global_creator=Bytes("creator") # byteslice
    global_seller=Bytes("seller") # byteslice
    global_arbiter=Bytes("arbiter") #byteslice
    global_buyer=Bytes("buyer") # byteslice
    global_app_id=Bytes("app_id") # byteslice
    # ^^^ ^^^ ^^^

    pull_out=Bytes("pull_out") # CONSTANT
    buyer_withdraw_funds=Bytes("buyer_withdraw_funds") # CONSTANT
    seller_withdraw_funds=Bytes("seller_withdraw_funds") # CONSTANT
    global_escrow_amount = Bytes("global_escrow_amount") # CONSTANT
    global_trigger_pull_out_called_counter = Bytes("global_trigger_pull_out_called_counter") # CONSTANT
    global_trigger_fund_account_called_counter = Bytes("global_trigger_fund_account_called_counter") # CONSTANT
    

    scratch_int = ScratchVar(TealType.uint64)
    
    @Subroutine(TealType.none)
    def trigger_pull_out():
        return Seq(
            scratch_int.store(App.globalGet(global_trigger_pull_out_called_counter)),
            If(
                And(
                    scratch_int.load() < Int(UINT64_MAX),
                    Txn.sender() == App.globalGet(global_buyer)
                )
            )
            .Then(
                Seq(
                    App.globalPut(global_trigger_pull_out_called_counter, App.globalGet(global_trigger_pull_out_called_counter) + Int(1)),
                    InnerTxnBuilder.Begin(),
                    InnerTxnBuilder.SetFields({
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.amount: App.globalGet(global_escrow_amount) - Global.min_txn_fee(),
                        TxnField.sender: Global.current_application_address(),
                        TxnField.receiver: Txn.sender(),  # Funds receiver
                        TxnField.fee: Global.min_txn_fee(),  # It has already been paid for
                    }),
                    InnerTxnBuilder.Submit()
                )
            )
            .Else(
                Reject()
            ),
            Approve()
        )

    @Subroutine(TealType.none)
    def trigger_seller_withdraw_funds():
        return Seq(
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

    @Subroutine(TealType.none)
    def trigger_buyer_withdraw_funds(): 
        return Seq(
            Approve()
        )

    @Subroutine(TealType.none)
    def trigger_fund_account():
        return Seq([
            scratch_int.store(App.globalGet(global_trigger_fund_account_called_counter)),
            If(
                And(
                    scratch_int.load() < Int(UINT64_MAX),
                    Gtxn[0].sender() == App.globalGet(global_buyer),
                    Gtxn[0].amount() == App.globalGet(global_escrow_amount),
                )
            )
            .Then(
                App.globalPut(global_trigger_fund_account_called_counter, App.globalGet(global_trigger_fund_account_called_counter) + Int(1))
            )
            .Else(
                Reject()
            ),
            Approve()
        ])

    return program.event(
        init=Seq(
            App.globalPut(global_creator, Txn.sender()),
            App.globalPut(global_app_id, Txn.application_id()),
            App.globalPut(Bytes("inspection_begin"), Btoi(Txn.application_args[0])),
            App.globalPut(Bytes("inspection_end"), Btoi(Txn.application_args[1])),
            App.globalPut(Bytes("inspection_extension"), Btoi(Txn.application_args[2])),
            App.globalPut(Bytes("closing_date"), Btoi(Txn.application_args[3])),
            App.globalPut(Bytes("closing_date_extension"), Btoi(Txn.application_args[4])),
            App.globalPut(Bytes("sale_price"), 
                If(Btoi(Txn.application_args[5]) > Btoi(Txn.application_args[6]))
                .Then(
                    Btoi(Txn.application_args[6])
                )
                .Else(
                    Reject()
                )
            ),
            App.globalPut(global_escrow_amount,
                If(Btoi(Txn.application_args[6]) > Int(2000))
                .Then(
                    Btoi(Txn.application_args[6])
                )
                .Else(
                    Int(2000)
                )
            ),
            App.globalPut(global_buyer, Txn.application_args[7]),
            App.globalPut(global_seller, Txn.application_args[8]),
            App.globalPut(global_arbiter, Txn.application_args[9]),
            App.globalPut(global_trigger_pull_out_called_counter, Int(0)),
            App.globalPut(global_trigger_fund_account_called_counter, Int(0)),
            Approve()
        ),
        no_op=Seq(
            Cond(
                [ Txn.application_args[0] == pull_out, trigger_pull_out() ],
                [ Txn.application_args[0] == seller_withdraw_funds, trigger_seller_withdraw_funds()],
                [ Txn.application_args[0] == buyer_withdraw_funds, trigger_buyer_withdraw_funds()],
                [ 
                    And(
                        Global.group_size() == Int(2),
                        Gtxn[0].type_enum() == TxnType.Payment
                    ),
                    trigger_fund_account()
                ]
            ),
            Reject()
        )
    )

def clear_state_program():
    return Approve()