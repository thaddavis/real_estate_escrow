./sandbox enter algod

SELLER=QHGMAMCTEHZ2RQV2DRXSPAKIIT3REVK46CHNDJSW6WNXJLSJ7BB76NHDGY

goal app call --app-id 93 --from $SELLER --app-arg "str:seller_withdraw_funds" --dryrun-dump -o tx.dr

