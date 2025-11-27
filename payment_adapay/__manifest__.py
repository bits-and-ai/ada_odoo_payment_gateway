{
    'name': 'ADA Payment',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'AdaPay Payment Gateway For Website',
    'description': "This module enables seamless payments through AdaPay, "
                   "ensuring secure and convenient online transactions.",
    'author': 'HeleusAI P.L.C',
    'website': 'https://erp.heleusai.com',
    'maintainer': 'Surafel Wubshet',
    'depends': ['payment', 'account'],
    'data': [
        'views/payment_adapay_templates.xml',
        'views/payment_method_data.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'data/payment_provider_data.xml',
        'data/invoice_payment_link.xml'
    ],
  
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
