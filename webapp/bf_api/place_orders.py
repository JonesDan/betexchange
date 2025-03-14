import betfairlightweight
from betfairlightweight import filters
import os
import logging

# # create trading instance (app key must be activated for streaming)
# app_key = os.environ['BF_API_KEY']
# username = os.environ['BF_USER']
# password = os.environ['BF_PWD']
# trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')

# # login
# trading.login()

# # update for test
# market_id = "1.237424960"
# selection_id = 47972


def place_order(trading, selection_id, b_l, market_id, size, price, sizeMin, result_queue):
    # placing an order
    instructions = []
    order_response = []

    limit_order = filters.limit_order(size=size, price=price, persistence_type="LAPSE", time_in_force="FILL_OR_KILL", min_fill_size=sizeMin)
    instruction = filters.place_instruction(
        order_type="LIMIT",
        selection_id=selection_id,
        side=b_l,
        limit_order=limit_order,
    )
    instructions.append(instruction)
    
    place_orders = trading.betting.place_orders(
        market_id=market_id, instructions=instructions  # list
    )

    order_response += place_orders.place_instruction_reports

    result = '\n'.join([f"Status: {order.status}, BetId: {order.bet_id}, Average Price Matched: {order.average_price_matched}" for order in order_response])
    result_queue.put(result)

    return(result)
    

# place_order(trading, orderlist)
# def update_order(bet_id):
#     # updating an order
#     instruction = filters.update_instruction(
#         bet_id=bet_id, new_persistence_type="PERSIST"
#     )
#     update_order = trading.betting.update_orders(
#         market_id=market_id, instructions=[instruction]
#     )

#     print(update_order.status)
#     for order in update_order.update_instruction_reports:
#         print("Status: %s" % order.status)


# def replace_order(bet_id):
#     # replacing an order
#     instruction = filters.replace_instruction(bet_id=bet_id, new_price=1.10)
#     replace_order = trading.betting.replace_orders(
#         market_id=market_id, instructions=[instruction]
#     )

#     print(replace_order.status)
#     for order in replace_order.replace_instruction_reports:
#         place_report = order.place_instruction_reports
#         cancel_report = order.cancel_instruction_reports
#         print(
#             "Status: %s, New BetId: %s, Average Price Matched: %s "
#             % (order.status, place_report.bet_id, place_report.average_price_matched)
#         )


# def cancel_order(bet_id):
#     # cancelling an order
#     instruction = filters.cancel_instruction(bet_id=bet_id, size_reduction=2.00)
#     cancel_order = trading.betting.cancel_orders(
#         market_id=market_id, instructions=[instruction]
#     )

#     print(cancel_order.status)
#     for cancel in cancel_order.cancel_instruction_reports:
#         print(
#             "Status: %s, Size Cancelled: %s, Cancelled Date: %s"
#             % (cancel.status, cancel.size_cancelled, cancel.cancelled_date)
#         )

# place_order()