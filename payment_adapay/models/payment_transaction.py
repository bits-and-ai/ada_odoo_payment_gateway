import logging
from werkzeug import urls
from odoo import api, models, _,fields
from odoo.exceptions import ValidationError
from odoo.addons.payment import utils as payment_utils

from werkzeug.urls import url_encode, url_join

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    adapay_type = fields.Char(string="AdaPay Transaction Type")
    adapay_uuid = fields.Char(string="AdaPay UUID", readonly=True)
    adapay_checkout_url = fields.Char(string="AdaPay Checkout URL", readonly=True)
    
    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator='-',
                           **kwargs):
        if provider_code == 'adapay':
            prefix = payment_utils.singularize_reference_prefix()
        return super()._compute_reference(provider_code, prefix=prefix,
                                          separator=separator, **kwargs)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return AdaPay-specific rendering values.
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'adapay':
            return res

        # Create order on AdaPay
        payload = self._adapay_prepare_order_request_payload()
        order_response = self.provider_id._adapay_make_request(self.provider_id.adapay_payment_initiate_endpoint, payload)
        
        if not order_response or not order_response.get('uuid'):
            raise ValidationError("AdaPay: " + _("Failed to create order on AdaPay."))
        
        # Store UUID and checkout URL for future reference
        self.adapay_uuid = order_response.get('uuid')
        self.adapay_checkout_url = order_response.get('checkout_url')
        
        # Prepare rendering values
        rendering_values = {
            'api_url': self.provider_id._adapay_get_api_url(),
            'uuid': self.adapay_uuid,
            'checkout_url': self.adapay_checkout_url,
        }
        return rendering_values

    def _adapay_prepare_order_request_payload(self):
        """ Prepare the payload for the order request.
        """
        base_url = self.provider_id.get_base_url()
        
        
        #return_url = url_join(base_url, '/payment/adapay/return')
        cancel_url = url_join(base_url, '/payment/adapay/cancel')
        callback_url = url_join(base_url, '/payment/adapay/webhook')
        return_url = url_join(base_url, '/payment/adapay/return')
        
        # Prepare the payload
        payload = {
            'data': {
                'redirect_url': return_url,
                'cancel_url': cancel_url,
                'success_url': return_url,
                'error_url': cancel_url,
                'order_reason': f"Payment for {self.reference}",
                'currency': self.currency_id.name,
                'email': self.partner_email or '',
                'first_name': self.partner_name.split(' ')[0] if self.partner_name else '',
                'last_name': ' '.join(self.partner_name.split(' ')[1:]) if self.partner_name and len(self.partner_name.split(' ')) > 1 else '',
                'nonce': f"odoo_{self.reference}_{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}",
                'order_detail': {
                    'amount': int(self.amount),
                    'description': f"Order {self.reference}",
                },
                'phone_number': self.partner_phone or '',
                'session_expired': "5000",
                'total_amount': str(int(self.amount)),
                'tx_ref': self.reference,
                'message': "Payment from Odoo",
            }
        }
        return payload

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on AdaPay data.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'adapay' or tx:
            return tx

        # Find the transaction based on the AdaPay UUID
        uuid = notification_data.get('uuid')
        
        if not uuid:
            raise ValidationError("AdaPay: " + _("Received data with missing UUID."))
        
        tx = self.search([('adapay_uuid', '=', uuid), ('provider_code', '=', 'adapay')])
        if not tx:
            raise ValidationError(
                "AdaPay: " + _("No transaction found matching UUID %s.", uuid)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on AdaPay data.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'adapay':
            return

        # Extract payment status
        status = notification_data.get('status')
        if status == 'success':
            self._set_done()
        elif status == 'pending':
            self._set_pending()
        elif status == 'failed':
            self._set_canceled("AdaPay: " + _("Payment was canceled or failed."))
        else:
            _logger.warning(
                "Received unrecognized payment status for transaction with reference %s: %s",
                self.reference, status
            )
            self._set_error("AdaPay: " + _("Received unrecognized payment status: %s", status))
