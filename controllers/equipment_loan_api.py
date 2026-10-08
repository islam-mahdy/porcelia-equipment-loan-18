import json

from odoo import http
from odoo.http import request

"""
    GET    /api/equipment/loans
    GET    /api/equipment/loans/<id>
    POST   /api/equipment/loans
    POST   /api/equipment/loans/<id>/confirm
    POST   /api/equipment/loans/<id>/cancel
    POST   /api/equipment/loans/<id>/return
"""


class EquipmentLoanAPI(http.Controller):


    # GET all loans

    @http.route(
        "/api/equipment/loans",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def get_loans(self, **params):

        try:
            domain = []

            if params.get("state"):
                domain.append(
                    ("state", "=", params["state"])
                )

            if params.get("overdue") in ("1", "true", "True"):
                domain.append(
                    ("is_overdue", "=", True)
                )

            if params.get("item_id"):
                domain.append(
                    (
                        "item_id", "=", int(params["item_id"])
                    )
                )

            print("Loan domain:", domain)

            loans = request.env["equipment.loan"].search(domain)

            print(f"Loans: {loans}")

            if not loans:
                return request.make_json_response({
                    "success": False,
                    "message": "There are no loans",
                }, status=404)

            result = []

            for loan in loans:

                result.append({
                    "id": loan.id,
                    "name": loan.name,
                    "item_id": loan.item_id.id,
                    "item_name": (
                        loan.item_id.display_name
                        if loan.item_id
                        else None
                    ),
                    "borrower_id": loan.borrower_id.id,
                    "borrower_name": (
                        loan.borrower_id.name
                        if loan.borrower_id
                        else None
                    ),
                    "date_start": loan.date_start,
                    "date_due": loan.date_due,
                    "date_return": loan.date_return,
                    "state": loan.state,
                    "is_overdue": loan.is_overdue,
                    "days_late": loan.days_late,
                    "penalty_amount": loan.penalty_amount,
                    "currency": (
                        loan.currency_id.name
                        if loan.currency_id
                        else None
                    ),
                })

            count = request.env["equipment.loan"].search_count(domain)

            return request.make_json_response({
                "success": True,
                "count": count,
                "results": result,
            }, status=200)

        except Exception as error:
            return request.make_json_response({
                "success": False,
                "message": "Could not retrieve loans",
                "error": str(error),
            }, status=500)



    # GET a specific loan

    @http.route(
        "/api/equipment/loans/<int:loan_id>",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def get_loan(self, loan_id):

        try:
            loan = request.env["equipment.loan"].browse(loan_id)

            if not loan.exists():
                return request.make_json_response({
                    "success": False,
                    "message": "Loan not found",
                }, status=404)


            return request.make_json_response({
                "success": True,
                "id": loan.id,
                "name": loan.name,
                "item_id": loan.item_id.id,
                "item_name": (
                    loan.item_id.display_name
                    if loan.item_id
                    else None
                ),
                "borrower_id": loan.borrower_id.id,
                "borrower_name": (
                    loan.borrower_id.name
                    if loan.borrower_id
                    else None
                ),
                "date_start": loan.date_start,
                "date_due": loan.date_due,
                "date_return": loan.date_return,
                "state": loan.state,
                "is_overdue": loan.is_overdue,
                "days_late": loan.days_late,
                "penalty_amount": loan.penalty_amount,
                "currency": (
                    loan.currency_id.name
                    if loan.currency_id
                    else None
                ),
            }, status=200)

        except Exception as error:
            return request.make_json_response({
                "success": False,
                "message": "Could not retrieve loan",
                "error": str(error),
            }, status=500)



    # CREATE loan

    @http.route(
        "/api/equipment/loans",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def create_loan(self):

        try:
            body = request.httprequest.data.decode("utf-8")

            print("Received body:", body)

            vals = json.loads(body)

            print("Received values:", vals)
            print("Type:", type(vals))

            if not vals.get("item_id"):
                return request.make_json_response({
                    "success": False,
                    "message": "item_id is required",
                }, status=400)

            if not vals.get("date_start"):
                return request.make_json_response({
                    "success": False,
                    "message": "date_start is required",
                }, status=400)

            if not vals.get("date_due"):
                return request.make_json_response({
                    "success": False,
                    "message": "date_due is required",
                }, status=400)

            loan_vals = {
                "item_id": int(vals["item_id"]),
                "borrower_id": int(
                    vals.get("borrower_id")
                    or request.env.user.id
                ),
                "date_start": vals["date_start"],
                "date_due": vals["date_due"],
                "notes": vals.get("notes"),
            }

            print("ORM values:", loan_vals)

            loan = request.env["equipment.loan"].create(loan_vals)

            print("Created loan:", loan)
            print("Created loan ID:", loan.id)

            if loan:
                return request.make_json_response({
                    "success": True,
                    "loan_id": loan.id,
                    "loan_name": loan.name,
                    "item_id": loan.item_id.id,
                    "item_name": loan.item_id.display_name,
                    "borrower_id": loan.borrower_id.id,
                    "borrower_name": loan.borrower_id.name,
                    "date_start": loan.date_start,
                    "date_due": loan.date_due,
                    "state": loan.state,
                    "message": "Loan created successfully",
                }, status=201)

            return request.make_json_response({
                "success": False,
                "message": "Loan could not be created",
            }, status=400)


        except Exception as error:
            return request.make_json_response({
                "success": False,
                "message": "Could not create loan",
                "error": str(error),
            }, status=500)



    # CONFIRM loan

    @http.route(
        "/api/equipment/loans/<int:loan_id>/confirm",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def confirm_loan(self, loan_id):

        try:
            loan = request.env["equipment.loan"].browse(loan_id)

            if not loan.exists():
                return request.make_json_response({
                    "success": False,
                    "message": "Loan not found",
                }, status=404)

            loan.action_confirm()

            return request.make_json_response({
                "success": True,
                "loan_id": loan.id,
                "loan_name": loan.name,
                "state": loan.state,
                "message": "Loan confirmed successfully",
            }, status=200)

        except Exception as error:
            return request.make_json_response({
                "success": False,
                "message": "Could not confirm loan",
                "error": str(error),
            }, status=500)



    # CANCEL loan

    @http.route(
        "/api/equipment/loans/<int:loan_id>/cancel",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def cancel_loan(self, loan_id):

        try:
            loan = request.env["equipment.loan"].browse(loan_id)

            if not loan.exists():
                return request.make_json_response({
                    "success": False,
                    "message": "Loan not found",
                }, status=404)

            loan.action_cancel()

            return request.make_json_response({
                "success": True,
                "loan_id": loan.id,
                "loan_name": loan.name,
                "state": loan.state,
                "message": "Loan cancelled successfully",
            }, status=200)


        except Exception as error:
            return request.make_json_response({
                "success": False,
                "message": "Could not cancel loan",
                "error": str(error),
            }, status=500)



    # RETURN loan

    @http.route(
        "/api/equipment/loans/<int:loan_id>/return",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def return_loan(self, loan_id):

        try:
            loan = request.env["equipment.loan"].browse(loan_id)

            if not loan.exists():
                return request.make_json_response({
                    "success": False,
                    "message": "Loan not found",
                }, status=404)


            body = request.httprequest.data.decode("utf-8")

            vals = json.loads(body) if body else {}

            print("Received values:", vals)
            print("Type:", type(vals))

            loan.action_return(
                date_return=vals.get("date_return"),
                condition_score=vals.get("condition_score"),
                note=vals.get("note"),
            )

            return request.make_json_response({
                "success": True,
                "loan_id": loan.id,
                "loan_name": loan.name,
                "state": loan.state,
                "date_return": loan.date_return,
                "condition_score": loan.condition_score,
                "message": "Loan returned successfully",
            }, status=200)


        except Exception as error:
            return request.make_json_response({
                "success": False,
                "message": "Could not return loan",
                "error": str(error),
            }, status=500)