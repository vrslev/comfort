frappe.ready(function(){
	$('.buy_now').on('click', (e) => {
		frappe.msgprint({
			title: __('Confirm'),
			message: __('Are you sure you want to proceed?'),
			primary_action:{
				'label': 'Proceed',
				action(){
					var si = $(e.currentTarget).data('buy-item')
					frappe.call({
						method: "accounting.accounting.doctype.sales_invoice.sales_invoice.update_sales_invoice",
						args: {
							item_name: null,
							qty: 0,
							si_name: si,
							submit: true
						},
						callback: (r) => {
							$(e.currentTarget).prop('disabled', false);
							window.location.reload()
							frappe.msgprint({
								title: 'Success',
								indicator: 'green',
								message: `<h6>Invoice: ${ si }</h6><p>Thank You for shopping :)</p>`
							});
						}
					})
				}
			}
		})
	})
})