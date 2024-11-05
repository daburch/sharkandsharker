KEEP_ALIVE_REQUEST = (
    "0800000001000000"  # This message is sent periodically from the server
)

KEEP_ALIVE_RESPONSE = (
    "0800000002000000"  # This message is recieved periodically from the server
)


MARKETPLACE_REQUEST_HEADER = "0000b70d"
MARKETPLACE_RESPONSE_HEADER = "0000b80d"

H_ITEM_ID = b"DesignDataItem:Id_Item_"
H_ITEM_PROPERTY = b"DesignDataItemPropertyType:Id_ItemPropertyType_Effect_"
H_LEADERBOARD_RANK = b"LeaderboardRankData:Id_LeaderboardRank_"
