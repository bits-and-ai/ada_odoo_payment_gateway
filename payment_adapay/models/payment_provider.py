import logging
import requests
from odoo import http
import random
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import binascii


_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('adapay', 'AdaPay')],
                            ondelete={'adapay': 'set default'},
                            help="The technical code of this payment provider",
                            string="Code")
    adapay_api_key = fields.Char(
        string="AdaPay API Key",
        help="The API key provided by AdaPay",
        required_if_provider='adapay',
    )
    adapay_environment = fields.Selection(
        string="AdaPay Environment",
        selection=[('test', 'Test'), ('prod', 'Production')],
        default='test',
        required_if_provider='adapay',
    )
    adapay_public_api_key = fields.Char(
        string="AdaPay Public API Key", help="The API key of the webservice user", required_if_provider='adapay',
        groups='base.group_system')
    adapay_checkout_api_url_test = fields.Char(
        string="AdaPay Test Checkout API URL",
        default="https://uat.api.addispay.et/checkout-api/v1",
        required_if_provider='adapay',
        )
    adapay_checkout_api_url_main = fields.Char(
        string="AdaPay Production Checkout API URL",
        default="https://api.addispay.et/checkout-api/v1",
        required_if_provider='adapay',
    )
    adapay_payment_initiate_endpoint = fields.Char(
        string="AdaPay Payment Initiate Endpoint",
        default="create-order",
        required_if_provider='adapay',
    )


    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['adapay'] = {'mode': 'unique', 'domain': [('type', '=', 'bank')]}
        return res
    
    # updated implementation

    def _adapay_get_api_url(self):
        """ Return the appropriate API URL according to the provider state.
        """
        self.ensure_one()
        if self.adapay_environment == 'prod':
            return self.adapay_checkout_api_url_main
        else:
            return self.adapay_checkout_api_url_test
        
    def _adapay_make_request(self, endpoint, data=None, method='POST'):
        """ Make a request to AdaPay API.
        """
        self.ensure_one()
        
        url = f"{self._adapay_get_api_url()}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Auth': self.adapay_api_key,
        }

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            else:
                response = requests.post(url, headers=headers, data=json.dumps(data) if data else None)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach the AdaPay API")
            raise ValidationError("Could not establish the connection to the API.")
        except requests.exceptions.HTTPError as error:
            _logger.exception("Invalid API request")
            raise ValidationError(
                "The communication with the API failed.\n"
                f"HTTP error: {error.response.status_code}\n"
                f"Message: {error.response.text}"
            )
        except (ValueError, TypeError):
            _logger.exception("Invalid response from API")
            raise ValidationError("AdaPay: " + _("Invalid response from the API."))
    
