from frappe import _


def get_data():
    return {
        'heatmap': True,
        'heatmap_message': _('This is based on transactions against this Customer. See timeline below for details'),
        'fieldname': 'customer',
        'transactions': [
            {
                'label': _('Sales Order'),
                'items': ['Sales Order']
            },
            {
                'label': _('Purchase Order'),
                'items': ['Purchase Order']
            }
        ]
    }
