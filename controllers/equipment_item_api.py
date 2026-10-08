# import json
from odoo import http
from odoo.http import request

"""
    GET /api/equipment/items
    GET /api/equipment/items/<id>
"""


class EquipmentItemAPI(http.Controller):


    # GET all equipment items
    @http.route(
        "/api/equipment/items",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def get_items(self, **params):

        try:
            domain = []

            if params.get("category_id"):
                domain.append(
                    (
                        "category_id", "=", int(params["category_id"])
                    )
                )

            if params.get("state"):
                domain.append(
                    ("state", "=", params["state"])
                )

            # print("Domain:", domain)


            items = request.env["equipment.item"].search(domain, order="name")

            print(f"Items: {items}")

            if not items:
                return request.make_json_response({
                    "success": False,
                    "message": "There are no equipment items",
                }, status=404)


            result = []

            for item in items:

                result.append({
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "category": (
                        item.category_id.display_name
                        if item.category_id
                        else None
                    ),
                    "state": item.state,
                    "condition_score": item.condition_score,
                    "daily_rate": item.daily_rate,
                    "currency": (
                        item.currency_id.name
                        if item.currency_id
                        else None
                    ),
                    "loan_count": item.loan_count,
                    "total_days_on_loan": item.total_days_on_loan,
                })

            count = request.env["equipment.item"].search_count(domain)

            return request.make_json_response({
                "success": True,
                "count": count,
                "results": result,
            }, status=200,)

        except Exception as error:
            # print("Error:", error)
            return request.make_json_response({
                    "success": False,
                    "message": "Could not retrieve equipment items",
                    "error": str(error),
            },status=500)



    # GET a specifc equipment


    @http.route(
        "/api/equipment/items/<int:item_id>",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def get_item(self, item_id):

        try:
            item = request.env["equipment.item"].browse(item_id)
            if not item.exists():
                return request.make_json_response({
                        "success": False,
                        "message": "Equipment item not found",
                }, status=404)

            return request.make_json_response({
                "success": True,
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "category": (
                    item.category_id.display_name
                    if item.category_id
                    else None
                ),
                "state": item.state,
                "condition_score": item.condition_score,
                "daily_rate": item.daily_rate,
                "currency": (
                    item.currency_id.name
                    if item.currency_id
                    else None
                ),
                "loan_count": item.loan_count,
                "total_days_on_loan": item.total_days_on_loan,
            }, status=200)


        except Exception as error:
            return request.make_json_response({
                "success": False,
                "message": "Could not retrieve item",
                "error": str(error),
            }, status=500)
