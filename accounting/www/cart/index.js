frappe.ready(function(){
	$('.buy_now').on('click', (e) => {
		frappe.msgprint({
			title: __('Notification'),
			message: __('Are you sure you want to proceed?'),
			primary_action:{
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
							location.reload();
							frappe.msgprint({
								title: 'Success',
								indicator: 'green',
								message: 'Thank You for shopping :)'
							});
						}
					})
				}
			}
		})
	})
})