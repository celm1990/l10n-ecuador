import json
import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayphoneController(http.Controller):
    _return_url = "/payment/payphone/return"

    @http.route(
        "/payment/payphone",
        type="json",
        methods=["POST"],
        auth="public",
        csrf=False,
        save_session=False,
    )
    def payphone_new_payment(self):
        data = request.dispatcher.jsonrequest
        _logger.info(data)
        payphone = request.env.ref("payment_payphone.payment_provider_payphone").sudo()
        Transaction = request.env["payment.transaction"].sudo()
        transaction = Transaction.create(
            {
                "provider_id": payphone.id,
                "amount": data.get("amount"),
                "reference": data.get("reference"),
                "partner_id": request.env.user.partner_id.id,
                "currency_id": request.env.company.currency_id.id,
            }
        )
        payload = transaction._payphone_prepare_preference_request_payload()
        payphone_response = transaction.provider_id._payphone_make_request(
            "button/Prepare", payload=payload
        )

        # Extract the payment link URL and params and embed them in the redirect form.
        transaction.write({"provider_reference": payphone_response.get("paymentId")})
        payphone_response.get("payWithPayPhone")
        json.dumps(payphone_response)
        return payphone_response

    @http.route(
        _return_url,
        type="http",
        methods=["GET"],
        auth="public",
        csrf=False,
        save_session=False,
    )
    def payphone_return_from_checkout(self, **data):
        """Process the notification data sent by Payphone after redirection from checkout.

        :param dict data: The notification data.
        """
        # Handle the notification data.
        _logger.info(
            "Handling redirection from Payphone with data:\n%s", pprint.pformat(data)
        )
        if data.get("clientTransactionId"):
            request.env["payment.transaction"].sudo()._handle_notification_data(
                "payphone", data
            )
        return request.redirect("/payment/status")
