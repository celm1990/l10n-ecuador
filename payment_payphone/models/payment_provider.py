import logging
import pprint

import requests
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("payphone", "Payphone")], ondelete={"payphone": "set default"}
    )
    payphone_access_token = fields.Char(
        required_if_provider="payphone",
        groups="base.group_system",
    )

    def _payphone_make_request(self, endpoint, payload=None, method="POST"):
        """Make a request to Payphone API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        url = urls.url_join("https://pay.payphonetodoesposible.com/api/", endpoint)
        headers = {"Authorization": f"Bearer {self.payphone_access_token}"}
        try:
            if method == "GET":
                response = requests.get(
                    url, params=payload, headers=headers, timeout=10
                )
            else:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    _logger.exception(
                        "Invalid API request at %s with data:\n%s",
                        url,
                        pprint.pformat(payload),
                    )
                    response_content = response.json()
                    message_list = []
                    if response_content.get("message"):
                        message_list.append(
                            f"Error Code: {response_content.get('errorCode')}. "
                            f"Descripcion: {response_content.get('message')}"
                        )
                    for messaje in response_content.get("errors", []):
                        msj = messaje.get("message")
                        msj_description = "".join(messaje.get("errorDescriptions"))
                        message_list.append(
                            f"Error Code: {msj}. Descripcion: {msj_description}"
                        )
                    raise ValidationError(
                        _(
                            "Payphone: The communication with the API failed. "
                            "Payphone gave us the following information: '%s'",
                            "\n".join(message_list),
                        )
                    ) from None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                _("Payphone: Could not establish the connection to the API.")
            ) from None
        return response.json()
