import logging
import pprint

from werkzeug.urls import url_encode

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
import json

_logger = logging.getLogger(__name__)


class AdaPayController(http.Controller):
    _return_url = '/payment/adapay/return'
    _cancel_url = '/payment/adapay/cancel'
    _webhook_url = '/payment/adapay/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def adapay_return_from_checkout(self, **post):
        """ Process the return from AdaPay after payment."""

        # If the request is a GET, simply redirect to the status page
        if request.httprequest.method == 'GET':
            return request.redirect('/payment/status')

        # For POST requests, process the returned JSON payload
        raw_data = request.httprequest.data
        data = json.loads(raw_data.decode('utf-8')) if raw_data else {}

        # Log the return data
        _logger.info("handling return from AdaPay with data:\n%s", pprint.pformat(data))

        uuid = data.get('session_uuid')
        if not uuid:
            raise ValidationError("AdaPay: Missing session_uuid in POST data")

        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('adapay_uuid', '=', uuid),
            ('provider_code', '=', 'adapay')
        ], limit=1)
        if not tx_sudo:
            raise ValidationError(f"AdaPay: No transaction found with UUID {uuid}")

        # Determine the status from the POST payload
        payment_status = data.get('payment_status', '').lower()
        if payment_status == 'success':
            status = 'success'
        elif payment_status == 'pending':
            status = 'pending'
        else:
            status = 'failed'

        # Process the notification to update the transaction status
        notification_data = {
            'uuid': uuid,
            'status': status,
        }
        tx_sudo._process_notification_data(notification_data)

        return request.redirect('/payment/status')

    @http.route(_cancel_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def adapay_cancel(self, **post):
        """ Process cancellation from AdaPay.
        """
        raw_data = request.httprequest.data
        data = json.loads(raw_data.decode('utf-8')) if raw_data else {}

        # Log the cancellation data
        _logger.info("handling cancel from AdaPay with data:\n%s", pprint.pformat(data))
        # Find the transaction based on the returned data
        try:
            uuid = data.get('uuid')
            if not uuid:
                raise ValidationError("AdaPay: Missing session_uuid in POST data")
                
            else:
                tx_sudo = request.env['payment.transaction'].sudo().search([
                    ('adapay_uuid', '=', uuid),
                    ('provider_code', '=', 'adapay')
                ])
                if not tx_sudo:
                    raise ValidationError(f"AdaPay: No transaction found with UUID {uuid}")
                
            # Process the notification data
            notification_data = {
                'uuid': uuid,
                'status': 'failed'
            }
            tx_sudo._process_notification_data(notification_data)
        except ValidationError as e:
            _logger.exception("Error processing AdaPay cancel data: %s", str(e))
            
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def adapay_webhook(self):
        """ Process the data sent by AdaPay to the webhook.
        """
        # Get the webhook data
        raw_data = request.httprequest.data
        data = json.loads(raw_data.decode('utf-8')) if raw_data else {}

        _logger.info("handling webhook notification from AdaPay with data:\n%s", pprint.pformat(data))
        
        # Find the transaction based on the webhook data
        try:
            uuid = data.get('uuid')
            if not uuid:
                raise ValidationError("AdaPay: Missing UUID in webhook data")
                
            tx_sudo = request.env['payment.transaction'].sudo().search([
                ('adapay_uuid', '=', uuid),
                ('provider_code', '=', 'adapay')
            ])
            
            if not tx_sudo:
                raise ValidationError(f"AdaPay: No transaction found with UUID {uuid}")
                
            # Process the notification data
            status = data.get('payment_status', '').lower()
            notification_data = {
                'uuid': uuid,
                'status': status
            }
            tx_sudo._process_notification_data(notification_data)
        except ValidationError as e:
            _logger.exception("Error processing AdaPay webhook data: %s", str(e))
            
        return request.make_response(
            json.dumps({'status': 'success'}),
            headers=[('Content-Type', 'application/json')]
        )



